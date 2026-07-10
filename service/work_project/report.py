"""Report generation service — produces a Word (.docx) security assessment report.

Receives a snapshot dict (from WorkProjectRecordSnapshotSchema.model_dump()),
returns (docx_bytes, filename).
"""
from __future__ import annotations

import io
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

# ── Chinese label mappings ──────────────────────────────────────────────────

PROJECT_TYPE = {"penetration_test": "渗透测试", "source_code_audit": "代码审计"}
PROJECT_STATUS = {"working": "进行中", "completed": "已完成", "canceled": "已取消"}

TASK_STATUS = {"todo": "待办", "in_progress": "进行中", "blocked": "受阻", "done": "完成"}

ASSET_TYPE = {"service": "服务", "domain": "域名", "network": "网络", "binary": "二进制"}
ASSET_ORIGIN = {"scope": "范围", "discovered": "发现"}

SEVERITY_LABEL = {
    "critical": "严重", "high": "高危", "medium": "中危",
    "low": "低危", "info": "信息",
}
SEVERITY_ORDER = ["critical", "high", "medium", "low", "info"]
SEVERITY_BG = {
    "critical": "FDE8E8",   # light red
    "high":    "FEEBC8",    # light orange
    "medium":  "FEFCBF",    # light yellow
    "low":     "BEE3F8",    # light blue
    "info":    "EDF2F7",    # light gray
}

FINDING_STATUS = {"suspected": "疑似", "validated": "已确认", "false_positive": "误报"}

EDGE_TYPE = {
    "related": "关联", "resolves_to": "解析至", "hosts": "托管",
    "connects_to": "连接至", "trusts": "信任",
    "exploits": "利用", "pivots_to": "跳转至", "leads_to": "导向",
}

ATTACK_PATH_STATUS = {
    "suspected": "疑似", "validated": "已确认",
    "blocked": "已阻止", "closed": "已关闭",
}


# ── Helper utilities ────────────────────────────────────────────────────────

def _set_cell_shading(cell, hex_color: str):
    """Set background shading of a table cell."""
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _set_paragraph_font(paragraph, size: float, bold: bool = False,
                        color: RGBColor | None = None,
                        font_name: str = "SimSun"):
    """Apply font settings to all runs in a paragraph."""
    for run in paragraph.runs:
        run.font.size = Pt(size)
        run.font.bold = bold
        run.font.name = font_name
        run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
        if color:
            run.font.color.rgb = color


def _add_heading_styled(doc: Document, text: str, level: int = 1):
    """Add a heading with custom Chinese-friendly styling."""
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.name = "SimHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
        if level == 1:
            run.font.size = Pt(16)
            run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)  # dark blue
        elif level == 2:
            run.font.size = Pt(13)
            run.font.color.rgb = RGBColor(0x2d, 0x37, 0x48)  # dark gray
    return heading


def _add_styled_table(doc: Document, headers: list[str], rows: list[list[str]],
                      col_widths: list[float] | None = None,
                      severity_col: int | None = None,
                      severity_values: list[str] | None = None):
    """Add a bordered table with gray header row."""
    if not rows:
        p = doc.add_paragraph("（无数据）")
        for run in p.runs:
            run.font.size = Pt(10.5)
            run.font.name = "SimSun"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
        return

    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    # Header row
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        run.font.size = Pt(10)
        run.font.bold = True
        run.font.name = "SimHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
        _set_cell_shading(cell, "F7FAFC")

    # Data rows
    for r_idx, row_data in enumerate(rows):
        for c_idx, val in enumerate(row_data):
            cell = table.rows[r_idx + 1].cells[c_idx]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(val) if val is not None else "")
            run.font.size = Pt(9)
            run.font.name = "SimSun"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
            # Severity coloring
            if severity_col is not None and c_idx == severity_col and severity_values:
                sev_key = severity_values[r_idx] if r_idx < len(severity_values) else None
                if sev_key and sev_key in SEVERITY_BG:
                    _set_cell_shading(cell, SEVERITY_BG[sev_key])

    # Column widths
    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                if i < len(row.cells):
                    row.cells[i].width = Cm(w)

    return table


# ── Section builders ────────────────────────────────────────────────────────

def _build_cover(doc: Document, project: dict):
    """Section 1: Cover page."""
    for _ in range(6):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("安全评估报告")
    run.font.size = Pt(24)
    run.font.bold = True
    run.font.name = "SimHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
    run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    doc.add_paragraph()

    # Project name
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(project.get("name", "未命名项目"))
    run.font.size = Pt(18)
    run.font.name = "SimHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")

    # Sub-info lines
    owners_list = project.get("owners", [])
    # owners can be list of dicts with "username" or list of strings
    if owners_list and isinstance(owners_list[0], dict):
        owner_names = ", ".join(o.get("username", str(o)) for o in owners_list)
    else:
        owner_names = ", ".join(str(o) for o in owners_list)

    info_lines = [
        f"项目类型：{PROJECT_TYPE.get(project.get('type', ''), project.get('type', '—'))}",
        f"项目状态：{PROJECT_STATUS.get(project.get('status', ''), project.get('status', '—'))}",
        f"负责人：{owner_names or '—'}",
        f"生成日期：{datetime.now().strftime('%Y年%m月%d日')}",
    ]
    for line in info_lines:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(line)
        run.font.size = Pt(12)
        run.font.name = "SimSun"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    doc.add_paragraph()
    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("破晓 安全评估平台")
    run.font.size = Pt(14)
    run.font.name = "SimHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
    run.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)

    doc.add_page_break()


def _build_overview(doc: Document, project: dict, records: dict):
    """Section 2: Project overview."""
    _add_heading_styled(doc, "一、项目概述", level=1)

    assets = records.get("assets", [])
    findings = records.get("findings", [])
    graph = records.get("graph", {})
    edges = graph.get("edges", [])
    attack_paths = graph.get("attack_paths", [])

    # Count agent sessions from project
    agent_sessions = project.get("agent_summaries", [])
    task_progress = project.get("progress", 0)

    owners_list = project.get("owners", [])
    if owners_list and isinstance(owners_list[0], dict):
        owner_names = ", ".join(o.get("username", str(o)) for o in owners_list)
    else:
        owner_names = ", ".join(str(o) for o in owners_list)

    overview_items = [
        ("项目名称", project.get("name", "—")),
        ("项目类型", PROJECT_TYPE.get(project.get("type", ""), project.get("type", "—"))),
        ("项目状态", PROJECT_STATUS.get(project.get("status", ""), project.get("status", "—"))),
        ("项目描述", project.get("description") or "—"),
        ("负责人", owner_names or "—"),
        ("整体进度", f"{task_progress}%"),
        ("资产数量", str(len(assets))),
        ("发现数量", str(len(findings))),
        ("关联边数量", str(len(edges))),
        ("攻击路径数量", str(len(attack_paths))),
        ("智能体会话", str(len(agent_sessions))),
    ]

    table = doc.add_table(rows=len(overview_items), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(overview_items):
        cell_l = table.rows[i].cells[0]
        cell_r = table.rows[i].cells[1]
        cell_l.text = ""
        cell_r.text = ""
        p_l = cell_l.paragraphs[0]
        run_l = p_l.add_run(label)
        run_l.font.size = Pt(10.5)
        run_l.font.bold = True
        run_l.font.name = "SimHei"
        run_l._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
        _set_cell_shading(cell_l, "F7FAFC")
        cell_l.width = Cm(3.5)

        p_r = cell_r.paragraphs[0]
        run_r = p_r.add_run(value)
        run_r.font.size = Pt(10.5)
        run_r.font.name = "SimSun"
        run_r._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    doc.add_paragraph()


def _build_tasks(doc: Document, project: dict):
    """Section 3: Task list."""
    _add_heading_styled(doc, "二、任务清单", level=1)

    tasks = project.get("tasks", [])
    if not tasks:
        p = doc.add_paragraph("（无任务）")
        for run in p.runs:
            run.font.size = Pt(10.5)
        return

    headers = ["序号", "任务标题", "状态", "进度"]
    rows = []
    for i, t in enumerate(tasks, 1):
        title = t.get("title", "—")
        status = TASK_STATUS.get(t.get("status", ""), t.get("status", "—"))
        progress = f"{t.get('progress', 0)}%"
        rows.append([str(i), title, status, progress])

    _add_styled_table(doc, headers, rows, col_widths=[1.5, 8, 2.5, 2])


def _build_findings(doc: Document, records: dict):
    """Section 4: Findings list, grouped by severity."""
    _add_heading_styled(doc, "三、发现清单", level=1)

    findings = records.get("findings", [])
    if not findings:
        p = doc.add_paragraph("（无发现）")
        for run in p.runs:
            run.font.size = Pt(10.5)
        return

    # Group by severity
    grouped: dict[str, list] = {}
    for f in findings:
        sev = f.get("severity", "info")
        grouped.setdefault(sev, []).append(f)

    # Ordered by severity
    for sev_key in SEVERITY_ORDER:
        group = grouped.get(sev_key, [])
        if not group:
            continue
        sev_label = SEVERITY_LABEL.get(sev_key, sev_key)
        _add_heading_styled(doc, f"{sev_label}（{len(group)} 项）", level=2)

        headers = ["序号", "标题", "状态", "关联资产", "描述"]
        rows = []
        sev_vals = []
        for i, f in enumerate(group, 1):
            title = f.get("title", "—")
            status = FINDING_STATUS.get(f.get("status", ""), f.get("status", "—"))
            asset_id = f.get("asset_id")
            # Find asset name
            asset_name = "—"
            if asset_id:
                for a in records.get("assets", []):
                    if a.get("id") == asset_id:
                        asset_name = a.get("identifier", "—")
                        break
            desc = f.get("description") or "—"
            # Truncate long descriptions
            if len(desc) > 120:
                desc = desc[:120] + "…"
            rows.append([str(i), title, status, asset_name, desc])
            sev_vals.append(sev_key)

        _add_styled_table(doc, headers, rows,
                          col_widths=[1.2, 4, 1.8, 3, 5],
                          severity_col=2, severity_values=sev_vals)
        doc.add_paragraph()


def _build_assets(doc: Document, records: dict):
    """Section 5: Asset list."""
    _add_heading_styled(doc, "四、资产清单", level=1)

    assets = records.get("assets", [])
    if not assets:
        p = doc.add_paragraph("（无资产）")
        for run in p.runs:
            run.font.size = Pt(10.5)
        return

    headers = ["序号", "资产标识", "类型", "来源", "主机", "端口", "横幅"]
    rows = []
    for i, a in enumerate(assets, 1):
        identifier = a.get("identifier", "—")
        atype = ASSET_TYPE.get(a.get("type", ""), a.get("type", "—"))
        origin = ASSET_ORIGIN.get(a.get("origin", ""), a.get("origin", "—"))
        host = a.get("host") or "—"
        port = str(a.get("port")) if a.get("port") else "—"
        # Banner can be in extra.banner or at top level
        extra = a.get("extra", {})
        banner = a.get("banner") or (extra.get("banner") if isinstance(extra, dict) else "") or "—"
        if len(banner) > 80:
            banner = banner[:80] + "…"
        rows.append([str(i), identifier, atype, origin, host, port, banner])

    _add_styled_table(doc, headers, rows,
                      col_widths=[1.2, 4, 1.5, 1.5, 3, 1.5, 4])


def _build_attack_paths(doc: Document, records: dict):
    """Section 6: Attack paths."""
    _add_heading_styled(doc, "五、攻击路径", level=1)

    graph = records.get("graph", {})
    attack_paths = graph.get("attack_paths", [])
    edges = graph.get("edges", [])
    attack_path_steps = graph.get("attack_path_steps", [])

    if not attack_paths:
        p = doc.add_paragraph("（无攻击路径）")
        for run in p.runs:
            run.font.size = Pt(10.5)
        return

    # Build edge lookup
    edge_map = {e.get("id"): e for e in edges}

    # Build asset lookup (for edge source/target names)
    assets = records.get("assets", [])
    asset_map = {a.get("id"): a for a in assets}

    # Build step lookup: path_id -> list of steps sorted by sequence
    steps_by_path: dict[int, list] = {}
    for step in attack_path_steps:
        pid = step.get("path_id")
        steps_by_path.setdefault(pid, []).append(step)
    for pid in steps_by_path:
        steps_by_path[pid].sort(key=lambda s: s.get("sequence", 0))

    for i, path in enumerate(attack_paths, 1):
        title = path.get("title") or f"攻击路径 {i}"
        status = ATTACK_PATH_STATUS.get(path.get("status", ""), path.get("status", "—"))
        summary = path.get("summary") or ""

        _add_heading_styled(doc, f"路径 {i}：{title}（{status}）", level=2)

        if summary:
            p = doc.add_paragraph()
            run = p.add_run(f"摘要：{summary}")
            run.font.size = Pt(10.5)
            run.font.name = "SimSun"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

        # Steps from attack_path_steps
        path_id = path.get("id")
        path_steps = steps_by_path.get(path_id, [])
        if path_steps:
            headers = ["步骤", "源→目标", "关系"]
            rows = []
            for s_idx, step in enumerate(path_steps, 1):
                edge = edge_map.get(step.get("edge_id"), {})
                # Resolve asset names from IDs
                src_id = edge.get("source_asset_id")
                tgt_id = edge.get("target_asset_id")
                src_name = asset_map.get(src_id, {}).get("identifier", str(src_id or "?"))
                tgt_name = asset_map.get(tgt_id, {}).get("identifier", str(tgt_id or "?"))
                # Truncate long identifiers
                if len(src_name) > 40:
                    src_name = src_name[:40] + "…"
                if len(tgt_name) > 40:
                    tgt_name = tgt_name[:40] + "…"
                rel = EDGE_TYPE.get(edge.get("type", ""), edge.get("type", "—"))
                rows.append([str(s_idx), f"{src_name} → {tgt_name}", rel])
            _add_styled_table(doc, headers, rows, col_widths=[1.5, 8, 3])

        doc.add_paragraph()


def _build_agent_summaries(doc: Document, project: dict):
    """Section 7: Agent summaries."""
    _add_heading_styled(doc, "六、智能体摘要", level=1)

    agents = project.get("agent_summaries", [])
    if not agents:
        p = doc.add_paragraph("（无智能体会话）")
        for run in p.runs:
            run.font.size = Pt(10.5)
        return

    for i, agent in enumerate(agents, 1):
        code = agent.get("agent_code") or agent.get("code", "—")
        _add_heading_styled(doc, f"智能体 {i}：{code}", level=2)

        # Build info table
        info_pairs = [
            ("当前任务", agent.get("current_task") or "—"),
            ("进度", f"{agent.get('progress', 0)}%"),
        ]
        # Extended summary fields
        summary = agent.get("summary") or agent.get("agent_summary") or {}
        if isinstance(summary, dict):
            for key, label in [
                ("findings", "发现"),
                ("decisions", "决策"),
                ("blockers", "阻碍"),
                ("next_steps", "下一步"),
                ("notes", "备注"),
            ]:
                val = summary.get(key)
                if val:
                    if isinstance(val, list):
                        val = "；".join(str(v) for v in val)
                    info_pairs.append((label, str(val)))
                elif key == "findings":
                    # Also check top-level findings_count
                    fc = agent.get("findings_count")
                    if fc is not None:
                        info_pairs.append(("发现数量", str(fc)))

        if info_pairs:
            table = doc.add_table(rows=len(info_pairs), cols=2)
            table.style = "Table Grid"
            for r_idx, (label, value) in enumerate(info_pairs):
                cell_l = table.rows[r_idx].cells[0]
                cell_r = table.rows[r_idx].cells[1]
                cell_l.text = ""
                cell_r.text = ""
                p_l = cell_l.paragraphs[0]
                run_l = p_l.add_run(label)
                run_l.font.size = Pt(10.5)
                run_l.font.bold = True
                run_l.font.name = "SimHei"
                run_l._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
                _set_cell_shading(cell_l, "F7FAFC")
                cell_l.width = Cm(3)

                p_r = cell_r.paragraphs[0]
                # Truncate very long values
                disp_val = value if len(value) <= 300 else value[:300] + "…"
                run_r = p_r.add_run(disp_val)
                run_r.font.size = Pt(10.5)
                run_r.font.name = "SimSun"
                run_r._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

        doc.add_paragraph()


def _build_statistics(doc: Document, project: dict, records: dict):
    """Section 8: Statistics and distribution tables."""
    _add_heading_styled(doc, "七、统计与分布", level=1)

    findings = records.get("findings", [])
    assets = records.get("assets", [])

    # 1. Severity distribution
    _add_heading_styled(doc, "发现严重程度分布", level=2)
    sev_counts: dict[str, int] = {}
    for f in findings:
        sev = f.get("severity", "info")
        sev_counts[sev] = sev_counts.get(sev, 0) + 1
    sev_rows = []
    sev_vals = []
    for sev_key in SEVERITY_ORDER:
        count = sev_counts.get(sev_key, 0)
        sev_rows.append([SEVERITY_LABEL.get(sev_key, sev_key), str(count)])
        sev_vals.append(sev_key)
    _add_styled_table(doc, ["严重程度", "数量"], sev_rows,
                      col_widths=[5, 3], severity_col=0, severity_values=sev_vals)

    doc.add_paragraph()

    # 2. Finding status distribution
    _add_heading_styled(doc, "发现状态分布", level=2)
    status_counts: dict[str, int] = {}
    for f in findings:
        st = f.get("status", "suspected")
        status_counts[st] = status_counts.get(st, 0) + 1
    status_rows = []
    for st_key in ["suspected", "validated", "false_positive"]:
        count = status_counts.get(st_key, 0)
        status_rows.append([FINDING_STATUS.get(st_key, st_key), str(count)])
    _add_styled_table(doc, ["状态", "数量"], status_rows, col_widths=[5, 3])

    doc.add_paragraph()

    # 3. Asset type distribution
    _add_heading_styled(doc, "资产类型分布", level=2)
    type_counts: dict[str, int] = {}
    for a in assets:
        at = a.get("type", "service")
        type_counts[at] = type_counts.get(at, 0) + 1
    type_rows = []
    for at_key in ["service", "domain", "network", "binary"]:
        count = type_counts.get(at_key, 0)
        type_rows.append([ASSET_TYPE.get(at_key, at_key), str(count)])
    _add_styled_table(doc, ["资产类型", "数量"], type_rows, col_widths=[5, 3])

    doc.add_paragraph()

    # 4. Asset origin distribution
    _add_heading_styled(doc, "资产来源分布", level=2)
    origin_counts: dict[str, int] = {}
    for a in assets:
        ao = a.get("origin", "scope")
        origin_counts[ao] = origin_counts.get(ao, 0) + 1
    origin_rows = []
    for ao_key in ["scope", "discovered"]:
        count = origin_counts.get(ao_key, 0)
        origin_rows.append([ASSET_ORIGIN.get(ao_key, ao_key), str(count)])
    _add_styled_table(doc, ["来源", "数量"], origin_rows, col_widths=[5, 3])


# ── Main entry ──────────────────────────────────────────────────────────────

async def generate_report(snapshot: dict) -> tuple[bytes, str]:
    """Generate a Word (.docx) report from a project snapshot.

    Returns (docx_bytes, filename) where filename is URL-safe Chinese.
    """
    project = snapshot.get("project", {})
    records = snapshot.get("records", {})

    doc = Document()

    # Set default font for the whole document
    style = doc.styles["Normal"]
    font = style.font
    font.name = "SimSun"
    font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    # Build sections
    _build_cover(doc, project)
    _build_overview(doc, project, records)
    _build_tasks(doc, project)
    _build_findings(doc, records)
    _build_assets(doc, records)
    _build_attack_paths(doc, records)
    _build_agent_summaries(doc, project)
    _build_statistics(doc, project, records)

    # Save to bytes
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    # Generate filename
    project_name = project.get("name", "未命名")
    # Sanitize filename — replace problematic chars
    safe_name = project_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Daybreak_安全评估报告_{safe_name}_{timestamp}.docx"

    return docx_bytes, filename
