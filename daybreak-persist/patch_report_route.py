#!/usr/bin/env python3
"""Patch router/work_project/projects.py to add the report generation endpoint.

Adds:
  - import for handler.work_project.report
  - import for StreamingResponse
  - Route function + router.add_api_route() call at the bottom

Idempotent: checks for existing import before patching.
"""
import sys
from pathlib import Path

# 支持 WSL 绝对路径 和 Docker 构建相对路径
_ROUTER_CANDIDATES = [
    "/home/AI/Z3r0/router/work_project/projects.py",       # WSL 直接部署
    "/app/router/work_project/projects.py",                 # Docker 容器内
    str(Path(__file__).resolve().parent.parent / "router" / "work_project" / "projects.py"),  # 相对路径
]

ROUTER_PATH = next((p for p in _ROUTER_CANDIDATES if Path(p).exists()), None)

def main():
    if ROUTER_PATH is None:
        print("Router file not found in any candidate path, skipping patch.")
        return
    with open(ROUTER_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # Check if already patched
    if "generate_work_project_report" in content:
        print("Router already patched with report route, skipping.")
        return

    # 1. Add imports after the existing import block
    # Find the last "from fastapi" import line
    import_block_end = 0
    for line in content.split("\n"):
        if line.startswith("from fastapi") or line.startswith("import fastapi"):
            import_block_end = content.find(line) + len(line)

    new_imports = (
        "\nfrom fastapi.responses import StreamingResponse"
        "\nfrom handler.work_project.report import generate_work_project_report"
    )

    # Insert after the last fastapi import
    content = content[:import_block_end] + new_imports + content[import_block_end:]

    # 2. Append route function and registration at the end
    route_code = '''

# ── Report generation endpoint ──────────────────────────────────────────────

async def generate_report_route(
    id: int,
    user: AuthUser = Depends(require_user),
) -> StreamingResponse:
    """Generate a Word (.docx) security assessment report for a work project."""
    return await generate_work_project_report(id=id, user=user)

router.add_api_route(
    "/{id}/generate-report",
    generate_report_route,
    methods=["POST"],
    responses={**COMMON_ERROR_RESPONSES, **NOT_FOUND_RESPONSE},
)
'''

    content = content.rstrip() + "\n" + route_code

    with open(ROUTER_PATH, "w", encoding="utf-8") as f:
        f.write(content)

    print("Router patched: report generation endpoint added.")


if __name__ == "__main__":
    main()
