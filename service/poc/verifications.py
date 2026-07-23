from __future__ import annotations

import asyncio
import base64
import json
import os
import re
import shlex
import signal
import time
from datetime import datetime
from typing import Any

import yaml
from sqlalchemy import String, cast, or_
from sqlmodel import select

from database import get_async_session
from model.host.hosts import ManagedHost
from model.poc.verifications import PocDefinition, PocRun
from model.sandbox.containers import SandboxContainer
from model.system_user.users import SystemUser
from schema.poc.verifications import (
    CreatePocRequest,
    PocExecutionMode,
    PocDefinitionSchema,
    PocRunSchema,
    PocRunStatus,
    RunPocRequest,
)
from schema.sandbox.containers import SandboxContainerStatus
from schema.system_user.users import SystemUserRole
from service.common.pagination import Page, paginate_statement
from service.sandbox.commands import SandboxContainerCommandTimeoutError, _execute_container_command
from service.sandbox.control_proxy import resolve_container_egress_environment
from service.sandbox.records import sandbox_container_can_manage


class PocValidationError(ValueError):
    pass


class PocExecutionError(ValueError):
    pass


NUCLEI_TEMPLATE_COMMAND = 'nuclei -silent -jsonl -u "{{target}}" -t <imported-template>'
NUCLEI_PROTOCOL_KEYS = (
    "http",
    "requests",
    "tcp",
    "network",
    "dns",
    "headless",
    "workflow",
    "code",
    "javascript",
)
DIRECT_UNSUPPORTED_PROTOCOLS = ("code", "javascript", "headless", "workflow")
YUQUE_CONVERSION_NOTICE = re.compile(
    r"\u7531\u8bed\u96c0\u8d44\u6599\u81ea\u52a8\u8f6c\u6362\u4e3a"
    r"\s*TscanPlus/Nuclei\s*\u53ef\u6267\u884c\u6a21\u677f[\u3002.]?\s*",
    re.IGNORECASE,
)
YUQUE_SOURCE_LINK = re.compile(
    r"\u539f\u6587[\uff1a:]\s*https?://www\.yuque\.com/hacktwo/dtdx2v/[^\s]+",
    re.IGNORECASE,
)


def parse_poc_document(content: str) -> CreatePocRequest:
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as yaml_error:
        try:
            data = json.loads(content)
        except json.JSONDecodeError as json_error:
            raise PocValidationError(f"invalid YAML/JSON: {json_error}") from yaml_error

    if not isinstance(data, dict):
        raise PocValidationError("PoC document must be an object")
    data = _json_compatible(data)

    if _is_nuclei_template(data):
        return _parse_nuclei_template(data)

    command = _first_string(data, "command", "cmd", "verify", "verification_command")
    if not command:
        raise PocValidationError("PoC document must include command")

    name = _first_string(data, "name", "id", "title") or "Imported PoC"
    tags = data.get("tags", [])
    if not isinstance(tags, list):
        tags = str(tags).split(",")

    return CreatePocRequest(
        name=name,
        description=_first_string(data, "description", "summary") or "",
        severity=_first_string(data, "severity", "level") or "unknown",
        category=_first_string(data, "category", "type") or "",
        tags=[str(item) for item in tags],
        command=command,
        raw_content=_json_compatible(data),
    )


async def create_poc(request: CreatePocRequest, *, user_id: int) -> PocDefinitionSchema:
    now = datetime.now()
    poc = PocDefinition(
        name=request.name,
        description=request.description,
        severity=request.severity or "unknown",
        category=request.category,
        tags=request.tags,
        command=request.command,
        raw_content=request.raw_content,
        created_by=user_id,
        created_at=now,
        updated_at=now,
    )
    async with get_async_session() as session:
        session.add(poc)
        await session.commit()
        await session.refresh(poc)
    return PocDefinitionSchema.model_validate(poc)


async def query_pocs(
    page: int,
    size: int,
    keyword: str = "",
    severity: str = "",
    category: str = "",
) -> Page[PocDefinitionSchema]:
    statement = select(PocDefinition).order_by(PocDefinition.id.desc())
    keyword = keyword.strip()
    if keyword:
        pattern = f"%{keyword}%"
        statement = statement.where(or_(
            PocDefinition.name.ilike(pattern),
            PocDefinition.description.ilike(pattern),
            PocDefinition.severity.ilike(pattern),
            PocDefinition.category.ilike(pattern),
            cast(PocDefinition.tags, String).ilike(pattern),
        ))
    if severity.strip():
        statement = statement.where(PocDefinition.severity == severity.strip().lower())
    if category.strip():
        statement = statement.where(PocDefinition.category == category.strip().lower())
    page_result = await paginate_statement(statement, page=page, size=size)
    return Page(
        page=page_result.page,
        size=page_result.size,
        total=page_result.total,
        items=[PocDefinitionSchema.model_validate(item) for item in page_result.items],
    )


async def delete_poc(id: int) -> bool:
    async with get_async_session() as session:
        poc = await session.get(PocDefinition, id)
        if poc is None:
            return False
        runs = (await session.exec(select(PocRun).where(PocRun.poc_id == id))).all()
        for run in runs:
            await session.delete(run)
        await session.delete(poc)
        await session.commit()
    return True


async def query_poc_runs(
    page: int,
    size: int,
    *,
    poc_id: int | None = None,
) -> Page[PocRunSchema]:
    statement = (
        select(PocRun, PocDefinition.name, SandboxContainer.container_name)
        .join(PocDefinition, PocRun.poc_id == PocDefinition.id)
        .outerjoin(SandboxContainer, PocRun.sandbox_container_id == SandboxContainer.id)
        .order_by(PocRun.id.desc())
    )
    if poc_id is not None:
        statement = statement.where(PocRun.poc_id == poc_id)
    page_result = await paginate_statement(statement, page=page, size=size)
    return Page(
        page=page_result.page,
        size=page_result.size,
        total=page_result.total,
        items=[_run_schema(
            row[0],
            poc_name=row[1],
            sandbox_container_name=row[2] or "Daybreak direct runner",
        ) for row in page_result.items],
    )


async def run_poc(
    id: int,
    request: RunPocRequest,
    *,
    user_id: int,
    user_role: SystemUserRole,
) -> PocRunSchema | None:
    async with get_async_session() as session:
        poc = await session.get(PocDefinition, id)
        if poc is None:
            return None
        direct = request.execution_mode == PocExecutionMode.DIRECT
        container = None
        host = None
        if direct:
            if user_role != SystemUserRole.ADMIN:
                raise PocExecutionError("direct execution requires administrator role")
            if not _is_direct_compatible_template(poc.raw_content):
                raise PocExecutionError(
                    "direct execution supports Nuclei network templates only; "
                    "code, javascript, headless, and workflow templates require a sandbox"
                )
        else:
            container = await session.get(SandboxContainer, request.sandbox_container_id)
            if container is None:
                raise PocExecutionError("sandbox container not found")
            if not sandbox_container_can_manage(container, user_id, user_role):
                raise PocExecutionError("no permission to use this sandbox container")
            if container.status != SandboxContainerStatus.RUNNING:
                raise PocExecutionError("sandbox container must be running")
            host = await session.get(ManagedHost, container.host_id)
            if host is None:
                raise PocExecutionError("managed host not found")

        display_command = render_poc_command(poc.command, request.target)
        execution_command = display_command
        if _is_nuclei_template(poc.raw_content):
            execution_command = render_poc_command(
                _build_nuclei_execution_command(poc.raw_content),
                request.target,
            )
        run = PocRun(
            poc_id=poc.id or 0,
            target=request.target,
            sandbox_container_id=None if direct else container.id,
            status=PocRunStatus.RUNNING.value,
            command=display_command,
            authorized_scope=request.authorized_scope,
            created_by=user_id,
            started_at=datetime.now(),
        )
        session.add(run)
        await session.commit()
        await session.refresh(run)

    started = time.monotonic()
    status = PocRunStatus.ERROR
    output = ""
    exit_code: int | None = None
    error = ""
    try:
        if direct:
            output, exit_code = await _execute_direct_nuclei(execution_command, request.timeout_seconds)
        else:
            environment = await resolve_container_egress_environment(container.id or request.sandbox_container_id)
            result = await _execute_container_command(
                host,
                container.container_hash,
                execution_command,
                environment,
                request.timeout_seconds,
            )
            output = result.output[-20000:]
            exit_code = result.exit_code
        if exit_code == 0:
            status = PocRunStatus.PASSED
        elif exit_code == 10:
            status = PocRunStatus.FAILED
        else:
            status = PocRunStatus.ERROR
            error = output.strip()[-1000:] or f"PoC runner exited with code {exit_code}"
    except SandboxContainerCommandTimeoutError as exc:
        error = str(exc)
    except Exception as exc:
        error = " ".join(str(exc).split())[:1000]

    async with get_async_session() as session:
        stored = await session.get(PocRun, run.id)
        if stored is None:
            raise PocExecutionError("PoC run disappeared before completion")
        stored.status = status.value
        stored.output = output
        stored.exit_code = exit_code
        stored.duration_ms = int((time.monotonic() - started) * 1000)
        stored.error = error
        stored.finished_at = datetime.now()
        session.add(stored)
        await session.commit()
        await session.refresh(stored)

        poc_name = (await session.exec(
            select(PocDefinition.name).where(PocDefinition.id == stored.poc_id)
        )).one()
        container_name = "Daybreak direct runner"
        if stored.sandbox_container_id is not None:
            container_name = (await session.exec(
                select(SandboxContainer.container_name).where(SandboxContainer.id == stored.sandbox_container_id)
            )).one()

    return _run_schema(stored, poc_name=poc_name, sandbox_container_name=container_name)


def render_poc_command(command: str, target: str) -> str:
    quoted_target = shlex.quote(target)
    rendered = command.replace("{{target}}", quoted_target).replace("{{ target }}", quoted_target)
    return f"TARGET={quoted_target}; export TARGET; {rendered}"


def _is_nuclei_template(data: dict[str, Any]) -> bool:
    return bool(data.get("id") and isinstance(data.get("info"), dict) and any(key in data for key in NUCLEI_PROTOCOL_KEYS))


def _is_direct_compatible_template(data: dict[str, Any]) -> bool:
    return _is_nuclei_template(data) and not any(key in data for key in DIRECT_UNSUPPORTED_PROTOCOLS)


def _parse_nuclei_template(data: dict[str, Any]) -> CreatePocRequest:
    info = data.get("info") or {}
    template_id = str(data.get("id") or "").strip()
    name = str(info.get("name") or template_id or "Imported Nuclei PoC").strip()
    description = str(info.get("description") or "").strip()
    severity = str(info.get("severity") or "unknown").strip().lower()
    raw_tags = info.get("tags", [])
    if isinstance(raw_tags, str):
        tags = [item.strip() for item in raw_tags.split(",") if item.strip()]
    elif isinstance(raw_tags, list):
        tags = [str(item).strip() for item in raw_tags if str(item).strip()]
    else:
        tags = []
    protocols = [key for key in NUCLEI_PROTOCOL_KEYS if key in data]
    category = f"nuclei-{protocols[0]}" if protocols else "nuclei"
    return CreatePocRequest(
        name=name[:255],
        description=description[:4000],
        severity=severity[:32] or "unknown",
        category=category[:128],
        tags=tags[:32],
        command=NUCLEI_TEMPLATE_COMMAND,
        raw_content=_json_compatible(data),
    )


def _json_compatible(data: dict[str, Any]) -> dict[str, Any]:
    def clean(value: Any) -> Any:
        if isinstance(value, str):
            return clean_poc_text(value)
        if isinstance(value, list):
            return [clean(item) for item in value]
        if isinstance(value, dict):
            return {str(key).replace("\x00", ""): clean(item) for key, item in value.items()}
        return value

    return json.loads(json.dumps(clean(data), ensure_ascii=False, default=str))


def clean_poc_text(value: str) -> str:
    value = value.replace("\x00", "")
    value = YUQUE_CONVERSION_NOTICE.sub("", value)
    value = YUQUE_SOURCE_LINK.sub("", value)
    return "\n".join(line.rstrip() for line in value.splitlines()).strip()


async def _execute_direct_nuclei(command: str, timeout_seconds: int) -> tuple[str, int]:
    process = await asyncio.create_subprocess_exec(
        "/bin/sh",
        "-lc",
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=os.environ.copy(),
        start_new_session=True,
    )
    try:
        stdout, _ = await asyncio.wait_for(process.communicate(), timeout=timeout_seconds)
    except TimeoutError as exc:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        await process.wait()
        raise SandboxContainerCommandTimeoutError(
            f"direct PoC verification timed out after {timeout_seconds}s"
        ) from exc
    return stdout.decode("utf-8", errors="replace")[-20000:], process.returncode or 0


def _build_nuclei_execution_command(template: dict[str, Any]) -> str:
    template_yaml = yaml.safe_dump(template, allow_unicode=True, sort_keys=False)
    encoded = base64.b64encode(template_yaml.encode("utf-8")).decode("ascii")
    encoded_arg = shlex.quote(encoded)
    return (
        "template_path=$(mktemp /tmp/daybreak-poc-XXXXXX.yaml); "
        "result_path=$(mktemp /tmp/daybreak-poc-result-XXXXXX.jsonl); "
        "error_path=$(mktemp /tmp/daybreak-poc-error-XXXXXX.log); "
        "cleanup() { rm -f \"$template_path\" \"$result_path\" \"$error_path\"; }; "
        "trap cleanup EXIT; "
        "nuclei_bin=\"${DAYBREAK_NUCLEI_BIN:-}\"; "
        "if [ -n \"$nuclei_bin\" ] && [ -x \"$nuclei_bin\" ]; then :; "
        "elif command -v nuclei >/dev/null 2>&1; then nuclei_bin=$(command -v nuclei); "
        "else "
        "echo 'nuclei is not installed in the Daybreak runtime or selected sandbox' >&2; exit 127; fi; "
        f"printf '%s' {encoded_arg} | base64 -d > \"$template_path\"; "
        "\"$nuclei_bin\" -silent -jsonl -no-color -duc -u \"$TARGET\" -t \"$template_path\" "
        ">\"$result_path\" 2>\"$error_path\"; scan_status=$?; "
        "cat \"$error_path\" >&2; cat \"$result_path\"; "
        "if [ \"$scan_status\" -ne 0 ]; then exit \"$scan_status\"; fi; "
        "if [ ! -s \"$result_path\" ]; then echo 'No vulnerability match' >&2; exit 10; fi"
    )


def _first_string(data: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _run_schema(run: PocRun, *, poc_name: str, sandbox_container_name: str) -> PocRunSchema:
    return PocRunSchema(
        id=run.id or 0,
        poc_id=run.poc_id,
        poc_name=poc_name,
        target=run.target,
        sandbox_container_id=run.sandbox_container_id,
        sandbox_container_name=sandbox_container_name,
        status=PocRunStatus(run.status),
        command=run.command,
        output=run.output,
        exit_code=run.exit_code,
        duration_ms=run.duration_ms,
        error=run.error,
        authorized_scope=run.authorized_scope,
        created_by=run.created_by,
        started_at=run.started_at,
        finished_at=run.finished_at,
    )
