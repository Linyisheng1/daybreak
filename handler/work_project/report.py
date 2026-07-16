"""Handler for work project report generation."""
from __future__ import annotations

import io
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from config import DATA_ROOT
from middleware.auth import AuthUser
from service.work_project.projects import get_work_project_record_snapshot_for_user
from service.work_project.report import generate_report


async def generate_work_project_report(id: int, user: AuthUser) -> StreamingResponse:
    """Generate a Word (.docx) report for a work project and return as download."""

    # 1. Load full record snapshot (reuse existing service)
    snapshot = await get_work_project_record_snapshot_for_user(
        id, user_id=user.id, user_role=user.role
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail="work project not found")

    # 2. Generate report document
    snapshot_dict = snapshot.model_dump(mode="json")
    docx_bytes, filename = await generate_report(snapshot_dict)

    # 3. Save to report directory
    report_dir = DATA_ROOT / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / filename).write_bytes(docx_bytes)

    # 4. Return as streaming download
    return StreamingResponse(
        io.BytesIO(docx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )
