"""Report generation service — produces a Word (.docx) security assessment report.

Receives a snapshot dict (from WorkProjectRecordSnapshotSchema.model_dump()),
returns (docx_bytes, filename).
"""
from __future__ import annotations

import io
import re
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, Cm, RGBColor, Emu
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
    "critical": "FDE8E8",
    "high":    "FEEBC8",
    "medium":  "FEFCBF",
    "low":     "BEE3F8",
    "info":    "EDF2F7",
}
SEVERITY_TEXT_COLOR = {
    "critical": RGBColor(0x9B, 0x1C, 0x1C),
    "high":    RGBColor(0x9C, 0x42, 0x22),
    "medium":  RGBColor(0x97, 0x5A, 0x0A),
    "low":     RGBColor(0x2B, 0x6C, 0xB0),
    "info":    RGBColor(0x4A, 0x55, 0x68),
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
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading)


def _add_run(paragraph, text: str, size: float = 9, bold: bool = False,
             color: RGBColor | None = None, font_name: str = "SimSun",
             italic: bool = False):
    """Add a styled run to a paragraph and return it."""
    run = paragraph.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.name = font_name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), font_name)
    if color:
        run.font.color.rgb = color
    return run


def _add_paragraph_styled(doc, text: str, size: float = 10.5, bold: bool = False,
                          color: RGBColor | None = None, font_name: str = "SimSun",
                          alignment=None, space_after: float = 6,
                          space_before: float = 0, italic: bool = False):
    """Add a fully styled paragraph."""
    p = doc.add_paragraph()
    if alignment is not None:
        p.alignment = alignment
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    _add_run(p, text, size=size, bold=bold, color=color, font_name=font_name, italic=italic)
    return p


def _add_heading_styled(doc: Document, text: str, level: int = 1):
    heading = doc.add_heading(text, level=level)
    for run in heading.runs:
        run.font.name = "SimHei"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
        if level == 1:
            run.font.size = Pt(16)
            run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)
        elif level == 2:
            run.font.size = Pt(13)
            run.font.color.rgb = RGBColor(0x2d, 0x37, 0x48)
        elif level == 3:
            run.font.size = Pt(11)
            run.font.color.rgb = RGBColor(0x4a, 0x55, 0x68)
    return heading


def _add_code_block(doc: Document, code_text: str):
    """Add a formatted code block with background shading and monospace font."""
    # Clean up the code text
    code_text = code_text.strip()
    if not code_text:
        return

    # Split into lines and add each as a paragraph in a code style
    lines = code_text.split('\n')
    for i, line in enumerate(lines):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.space_after = Pt(1)
        pf.space_before = Pt(1)
        pf.left_indent = Cm(0.5)
        # Set paragraph shading (light gray background)
        pPr = p._element.get_or_add_pPr()
        shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F4F8" w:val="clear"/>')
        pPr.append(shading)
        run = p.add_run(line if line else " ")
        run.font.size = Pt(8.5)
        run.font.name = "Consolas"
        run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
        run.font.color.rgb = RGBColor(0x2d, 0x37, 0x48)


def _parse_code_blocks(text: str):
    """Parse text containing code blocks marked with backticks or indentation.

    Returns list of (type, content) tuples where type is 'text' or 'code'.
    Handles:
    - ```...``` fenced code blocks
    - Inline `code` (shorter than 30 chars kept inline, longer become blocks)
    - Lines starting with whitespace that look like code (file paths, SQL, PHP etc.)
    """
    segments = []

    # Handle fenced code blocks (```...```)
    parts = re.split(r'(```[\s\S]*?```)', text)
    for part in parts:
        if part.startswith('```') and part.endswith('```'):
            # Strip the fence markers
            code = part[3:-3]
            # Remove language hint from first line if present
            lines = code.split('\n')
            if lines and re.match(r'^[a-z]{1,20}$', lines[0].strip()):
                lines = lines[1:]
            code = '\n'.join(lines)
            segments.append(('code', code))
        else:
            # Handle inline backtick code
            inline_parts = re.split(r'(`[^`]+`)', part)
            for ip in inline_parts:
                if ip.startswith('`') and ip.endswith('`') and len(ip) > 2:
                    code_content = ip[1:-1]
                    if len(code_content) > 40 or '\n' in code_content:
                        segments.append(('code', code_content))
                    else:
                        segments.append(('inline_code', code_content))
                else:
                    if ip:
                        segments.append(('text', ip))

    # If no code blocks found, check for code-like patterns in the raw text
    if not any(t == 'code' for t, _ in segments):
        segments = _parse_code_patterns(text)

    return segments


def _parse_code_patterns(text: str):
    """Fallback: detect code patterns in plain text and split into text/code segments."""
    segments = []
    lines = text.split('\n')
    current_text = []
    current_code = []

    code_indicators = [
        r'^\s*\$DB->', r'^\s*SELECT\s', r'^\s*INSERT\s', r'^\s*UPDATE\s',
        r'^\s*DELETE\s', r'^\s*<?php', r'^\s*\$', r'^\s*function\s',
        r'^\s*if\s*\(', r'^\s*return\s', r'^\s*echo\s',
        r'^\s*\{', r'^\s*\}', r'^\s*//', r'^\s*#',
        r'^\s*\*\s', r'^\s*/\*', r'^\s*\*/',
        r':\d+\s', r'\$_(POST|GET|REQUEST|SERVER|COOKIE|SESSION)',
        r'->[a-zA-Z_]+', r'=\s*new\s',
    ]

    in_code = False
    for line in lines:
        is_code_line = False
        for pattern in code_indicators:
            if re.search(pattern, line, re.IGNORECASE):
                is_code_line = True
                break
        # Lines starting with significant whitespace and containing code chars
        if line.startswith('  ') or line.startswith('\t'):
            if re.search(r'[;{}=<>$]', line):
                is_code_line = True

        if is_code_line:
            if current_text:
                text_content = '\n'.join(current_text).strip()
                if text_content:
                    segments.append(('text', text_content))
                current_text = []
            current_code.append(line)
        else:
            if current_code:
                code_content = '\n'.join(current_code).strip()
                if code_content:
                    segments.append(('code', code_content))
                current_code = []
            current_text.append(line)

    if current_text:
        text_content = '\n'.join(current_text).strip()
        if text_content:
            segments.append(('text', text_content))
    if current_code:
        code_content = '\n'.join(current_code).strip()
        if code_content:
            segments.append(('code', code_content))

    return segments


def _render_rich_text(doc: Document, text: str, default_size: float = 10,
                      default_font: str = "SimSun"):
    """Render text with code blocks and formatting into the document."""
    if not text:
        return

    segments = _parse_code_blocks(text)

    for seg_type, content in segments:
        if seg_type == 'code':
            _add_code_block(doc, content)
        elif seg_type == 'inline_code':
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.space_after = Pt(2)
            pf.space_before = Pt(2)
            pf.left_indent = Cm(0.3)
            pPr = p._element.get_or_add_pPr()
            shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="F0F4F8" w:val="clear"/>')
            pPr.append(shading)
            run = p.add_run(content)
            run.font.size = Pt(8.5)
            run.font.name = "Consolas"
            run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
            run.font.color.rgb = RGBColor(0xc5, 0x32, 0x22)
        else:
            # Regular text - split by newlines for separate paragraphs
            # But handle numbered lists and bullet points
            sub_lines = content.split('\n')
            for line in sub_lines:
                line = line.strip()
                if not line:
                    continue
                p = doc.add_paragraph()
                pf = p.paragraph_format
                pf.space_after = Pt(3)
                pf.space_before = Pt(1)
                pf.left_indent = Cm(0.3)
                # Detect numbered items like "1." "2)" etc.
                numbered = re.match(r'^(\d+[\.\)])\s*(.*)', line)
                if numbered:
                    _add_run(p, numbered.group(1) + " ", size=default_size,
                             bold=True, font_name=default_font)
                    _add_run(p, numbered.group(2), size=default_size,
                             font_name=default_font)
                elif line.startswith('- ') or line.startswith('• '):
                    _add_run(p, "• ", size=default_size, font_name=default_font)
                    _add_run(p, line[2:], size=default_size, font_name=default_font)
                else:
                    # Check for bold markers like **text**
                    _render_inline_formatting(p, line, default_size, default_font)


def _render_inline_formatting(paragraph, text: str, size: float = 10,
                              font_name: str = "SimSun"):
    """Render text with **bold** inline formatting."""
    parts = re.split(r'(\*\*[^*]+\*\*)', text)
    for part in parts:
        if part.startswith('**') and part.endswith('**'):
            _add_run(paragraph, part[2:-2], size=size, bold=True, font_name=font_name)
        elif part:
            _add_run(paragraph, part, size=size, font_name=font_name)


def _add_styled_table(doc: Document, headers: list[str], rows: list[list[str]],
                      col_widths: list[float] | None = None,
                      severity_col: int | None = None,
                      severity_values: list[str] | None = None):
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
        _set_cell_shading(cell, "EDF2F7")

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
            if severity_col is not None and c_idx == severity_col and severity_values:
                sev_key = severity_values[r_idx] if r_idx < len(severity_values) else None
                if sev_key and sev_key in SEVERITY_BG:
                    _set_cell_shading(cell, SEVERITY_BG[sev_key])

    if col_widths:
        for row in table.rows:
            for i, w in enumerate(col_widths):
                if i < len(row.cells):
                    row.cells[i].width = Cm(w)

    return table


def _add_severity_badge(paragraph, severity: str):
    """Add a colored severity badge as inline text."""
    label = SEVERITY_LABEL.get(severity, severity)
    color = SEVERITY_TEXT_COLOR.get(severity, RGBColor(0x4A, 0x55, 0x68))
    run = paragraph.add_run(f" [{label}] ")
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.name = "SimHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
    run.font.color.rgb = color
    return run


def _add_kv_table(doc: Document, pairs: list[tuple[str, str]],
                  label_width: float = 3.0, value_width: float = 14.0):
    """Add a key-value table with styled label column."""
    table = doc.add_table(rows=len(pairs), cols=2)
    table.style = "Table Grid"
    for i, (label, value) in enumerate(pairs):
        cell_l = table.rows[i].cells[0]
        cell_r = table.rows[i].cells[1]
        cell_l.text = ""
        cell_r.text = ""

        p_l = cell_l.paragraphs[0]
        _add_run(p_l, label, size=10, bold=True, font_name="SimHei")
        _set_cell_shading(cell_l, "EDF2F7")
        cell_l.width = Cm(label_width)

        p_r = cell_r.paragraphs[0]
        _add_run(p_r, str(value) if value else "—", size=10, font_name="SimSun")
        cell_r.width = Cm(value_width)

    return table


# ── Section builders ────────────────────────────────────────────────────────

def _build_cover(doc: Document, project: dict):
    for _ in range(6):
        doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("安全评估报告")
    run.font.size = Pt(26)
    run.font.bold = True
    run.font.name = "SimHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")
    run.font.color.rgb = RGBColor(0x1a, 0x36, 0x5d)

    doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run(project.get("name", "未命名项目"))
    run.font.size = Pt(18)
    run.font.name = "SimHei"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimHei")

    owners_list = project.get("owners", [])
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
    _add_heading_styled(doc, "一、项目概述", level=1)

    assets = records.get("assets", [])
    findings = records.get("findings", [])
    graph = records.get("graph", {})
    edges = graph.get("edges", [])
    attack_paths = graph.get("attack_paths", [])

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

    _add_kv_table(doc, overview_items, label_width=3.5, value_width=13.5)
    doc.add_paragraph()


def _build_tasks(doc: Document, project: dict):
    _add_heading_styled(doc, "二、任务清单", level=1)

    tasks = project.get("tasks", [])
    if not tasks:
        _add_paragraph_styled(doc, "（无任务）")
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
    _add_heading_styled(doc, "三、发现清单", level=1)

    findings = records.get("findings", [])
    if not findings:
        _add_paragraph_styled(doc, "（无发现）")
        return

    # ── Summary table ──
    _add_heading_styled(doc, "3.1 漏洞概览", level=2)
    headers = ["序号", "标题", "严重程度", "状态", "关联资产"]
    rows = []
    sev_vals = []
    for i, f in enumerate(findings, 1):
        title = f.get("title", "—")
        sev = f.get("severity", "info")
        status = FINDING_STATUS.get(f.get("status", ""), f.get("status", "—"))
        asset_id = f.get("asset_id")
        asset_name = "—"
        if asset_id:
            for a in records.get("assets", []):
                if a.get("id") == asset_id:
                    asset_name = a.get("identifier", "—")
                    break
        rows.append([str(i), title, SEVERITY_LABEL.get(sev, sev), status, asset_name])
        sev_vals.append(sev)

    _add_styled_table(doc, headers, rows,
                      col_widths=[1.2, 6, 2, 2, 3],
                      severity_col=2, severity_values=sev_vals)
    doc.add_paragraph()

    # ── Detailed findings ──
    _add_heading_styled(doc, "3.2 漏洞详情", level=2)

    # Group by severity for detailed display
    grouped: dict[str, list] = {}
    for f in findings:
        sev = f.get("severity", "info")
        grouped.setdefault(sev, []).append(f)

    global_idx = 0
    for sev_key in SEVERITY_ORDER:
        group = grouped.get(sev_key, [])
        if not group:
            continue
        sev_label = SEVERITY_LABEL.get(sev_key, sev_key)

        for f in group:
            global_idx += 1
            title = f.get("title", "未命名")
            status = FINDING_STATUS.get(f.get("status", ""), f.get("status", "—"))
            asset_id = f.get("asset_id")
            asset_name = "—"
            if asset_id:
                for a in records.get("assets", []):
                    if a.get("id") == asset_id:
                        asset_name = a.get("identifier", "—")
                        break

            # Finding header with colored severity
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.space_before = Pt(12)
            pf.space_after = Pt(4)
            _add_run(p, f"发现 #{global_idx}：", size=12, bold=True,
                     font_name="SimHei", color=RGBColor(0x1a, 0x36, 0x5d))
            _add_run(p, title, size=12, bold=True, font_name="SimHei")
            _add_severity_badge(p, sev_key)

            # Metadata table
            meta_pairs = [
                ("严重程度", sev_label),
                ("状态", status),
                ("关联资产", asset_name),
                ("发现来源", f.get("created_by_agent_code", "—") or "—"),
            ]
            _add_kv_table(doc, meta_pairs, label_width=2.5, value_width=14.5)

            # Description (FULL, no truncation)
            desc = f.get("description") or ""
            if desc:
                _add_paragraph_styled(doc, "漏洞描述", size=10.5, bold=True,
                                      font_name="SimHei", space_before=8, space_after=4)
                _render_rich_text(doc, desc, default_size=10)

            # Impact (FULL, no truncation)
            impact = f.get("impact") or ""
            if impact:
                _add_paragraph_styled(doc, "影响分析", size=10.5, bold=True,
                                      font_name="SimHei", space_before=8, space_after=4)
                p = doc.add_paragraph()
                pf = p.paragraph_format
                pf.space_after = Pt(4)
                pf.left_indent = Cm(0.3)
                _add_run(p, impact, size=10, font_name="SimSun",
                         color=RGBColor(0x9B, 0x2C, 0x2C))

            # Separator
            p = doc.add_paragraph()
            pf = p.paragraph_format
            pf.space_before = Pt(4)
            pf.space_after = Pt(4)
            run = p.add_run("─" * 60)
            run.font.size = Pt(6)
            run.font.color.rgb = RGBColor(0xC0, 0xC0, 0xC0)


def _build_assets(doc: Document, records: dict):
    _add_heading_styled(doc, "四、资产清单", level=1)

    assets = records.get("assets", [])
    if not assets:
        _add_paragraph_styled(doc, "（无资产）")
        return

    headers = ["序号", "资产标识", "类型", "来源", "主机", "端口", "横幅"]
    rows = []
    for i, a in enumerate(assets, 1):
        identifier = a.get("identifier", "—")
        atype = ASSET_TYPE.get(a.get("type", ""), a.get("type", "—"))
        origin = ASSET_ORIGIN.get(a.get("origin", ""), a.get("origin", "—"))
        host = a.get("host") or "—"
        port = str(a.get("port")) if a.get("port") else "—"
        extra = a.get("extra", {})
        banner = a.get("banner") or (extra.get("banner") if isinstance(extra, dict) else "") or "—"
        rows.append([str(i), identifier, atype, origin, host, port, banner])

    _add_styled_table(doc, headers, rows,
                      col_widths=[1.2, 4, 1.5, 1.5, 3, 1.5, 4])


def _build_attack_paths(doc: Document, records: dict):
    _add_heading_styled(doc, "五、攻击路径", level=1)

    graph = records.get("graph", {})
    attack_paths = graph.get("attack_paths", [])
    edges = graph.get("edges", [])
    attack_path_steps = graph.get("attack_path_steps", [])

    if not attack_paths:
        _add_paragraph_styled(doc, "（无攻击路径）")
        return

    edge_map = {e.get("id"): e for e in edges}
    assets = records.get("assets", [])
    asset_map = {a.get("id"): a for a in assets}

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
            _add_paragraph_styled(doc, f"摘要：{summary}", size=10.5, space_after=6)

        path_id = path.get("id")
        path_steps = steps_by_path.get(path_id, [])
        if path_steps:
            headers = ["步骤", "源→目标", "关系"]
            rows = []
            for s_idx, step in enumerate(path_steps, 1):
                edge = edge_map.get(step.get("edge_id"), {})
                src_id = edge.get("source_asset_id")
                tgt_id = edge.get("target_asset_id")
                src_name = asset_map.get(src_id, {}).get("identifier", str(src_id or "?"))
                tgt_name = asset_map.get(tgt_id, {}).get("identifier", str(tgt_id or "?"))
                rel = EDGE_TYPE.get(edge.get("type", ""), edge.get("type", "—"))
                rows.append([str(s_idx), f"{src_name} → {tgt_name}", rel])
            _add_styled_table(doc, headers, rows, col_widths=[1.5, 8, 3])

        doc.add_paragraph()


def _build_agent_summaries(doc: Document, project: dict):
    _add_heading_styled(doc, "六、智能体摘要", level=1)

    agents = project.get("agent_summaries", [])
    if not agents:
        _add_paragraph_styled(doc, "（无智能体会话）")
        return

    for i, agent in enumerate(agents, 1):
        code = agent.get("agent_code") or agent.get("code", "—")
        _add_heading_styled(doc, f"智能体 {i}：{code}", level=2)

        info_pairs = [
            ("当前任务", agent.get("current_task") or "—"),
            ("进度", f"{agent.get('progress', 0)}%"),
        ]
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
                _add_run(p_l, label, size=10, bold=True, font_name="SimHei")
                _set_cell_shading(cell_l, "EDF2F7")
                cell_l.width = Cm(3)

                p_r = cell_r.paragraphs[0]
                _add_run(p_r, value, size=10, font_name="SimSun")
                cell_r.width = Cm(14)

        doc.add_paragraph()


def _build_statistics(doc: Document, project: dict, records: dict):
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
    project = snapshot.get("project", {})
    records = snapshot.get("records", {})

    doc = Document()

    # Set default font
    style = doc.styles["Normal"]
    font = style.font
    font.name = "SimSun"
    font.size = Pt(10.5)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _build_cover(doc, project)
    _build_overview(doc, project, records)
    _build_tasks(doc, project)
    _build_findings(doc, records)
    _build_assets(doc, records)
    _build_attack_paths(doc, records)
    _build_agent_summaries(doc, project)
    _build_statistics(doc, project, records)

    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    project_name = project.get("name", "未命名")
    safe_name = project_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Daybreak_安全评估报告_{safe_name}_{timestamp}.docx"

    return docx_bytes, filename
