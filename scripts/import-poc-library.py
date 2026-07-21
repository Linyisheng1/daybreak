#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from sqlmodel import select

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import close_engine, get_async_session, init_engine
from config import load_config
from model.poc.verifications import PocDefinition
from service.poc.verifications import PocValidationError, _json_compatible, clean_poc_text, parse_poc_document


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import YAML/JSON PoCs into Daybreak")
    parser.add_argument("paths", nargs="+", type=Path, help="PoC files or directories")
    parser.add_argument("--user-id", type=int, required=True, help="Owning Daybreak user id")
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def iter_documents(paths: list[Path]):
    seen_paths: set[Path] = set()
    for source in paths:
        candidates = [source] if source.is_file() else source.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in {".yaml", ".yml", ".json"}:
                continue
            if path.name == "conversion-manifest.json":
                continue
            resolved = path.resolve()
            if resolved in seen_paths:
                continue
            seen_paths.add(resolved)
            yield path


def document_key(raw_content: dict, path: Path) -> str:
    template_id = str(raw_content.get("id") or "").strip()
    return f"nuclei:{template_id}" if template_id else f"file:{path.resolve()}"


async def import_library(args: argparse.Namespace) -> dict:
    load_config()
    init_engine()
    report = {
        "scanned": 0,
        "imported": 0,
        "duplicates": 0,
        "invalid": 0,
        "cleaned_existing": 0,
        "errors": [],
    }
    async with get_async_session() as session:
        existing_pocs = (await session.exec(select(PocDefinition))).all()
        existing_rows = []
        for poc in existing_pocs:
            cleaned = _json_compatible(poc.raw_content)
            existing_rows.append(cleaned)
            cleaned_description = clean_poc_text(poc.description)
            if cleaned != poc.raw_content or cleaned_description != poc.description:
                poc.raw_content = cleaned
                poc.description = cleaned_description
                session.add(poc)
                report["cleaned_existing"] += 1
        if report["cleaned_existing"] and not args.dry_run:
            await session.commit()
    known_keys = {
        f"nuclei:{str(raw.get('id')).strip()}"
        for raw in existing_rows
        if isinstance(raw, dict) and raw.get("id")
    }

    pending: list[PocDefinition] = []

    async def flush() -> None:
        if not pending or args.dry_run:
            pending.clear()
            return
        async with get_async_session() as session:
            session.add_all(pending)
            await session.commit()
        pending.clear()

    for path in iter_documents(args.paths):
        report["scanned"] += 1
        try:
            request = parse_poc_document(path.read_text(encoding="utf-8"))
            key = document_key(request.raw_content, path)
            if key in known_keys:
                report["duplicates"] += 1
                continue
            known_keys.add(key)
            now = datetime.now()
            pending.append(PocDefinition(
                name=request.name,
                description=request.description,
                severity=request.severity or "unknown",
                category=request.category,
                tags=request.tags,
                command=request.command,
                raw_content=request.raw_content,
                created_by=args.user_id,
                created_at=now,
                updated_at=now,
            ))
            report["imported"] += 1
            if len(pending) >= args.batch_size:
                await flush()
        except (OSError, UnicodeError, PocValidationError, ValueError) as exc:
            report["invalid"] += 1
            if len(report["errors"]) < 50:
                report["errors"].append({"path": str(path), "error": str(exc)})
    await flush()
    return report


def main() -> None:
    args = parse_args()
    async def run() -> dict:
        try:
            return await import_library(args)
        finally:
            await close_engine()

    report = asyncio.run(run())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["invalid"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
