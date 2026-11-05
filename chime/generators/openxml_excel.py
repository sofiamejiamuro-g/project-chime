"""Zero-Dependency OpenXML Multi-Tab Excel Workbook Generator for Manual QA."""

import os
import zipfile
import xml.sax.saxutils as saxutils
from typing import Dict, Any, List, Optional

QA_HEADERS = [
    'Test Case ID',
    'Sub-Agent Journey',
    'Test Name',
    'Scenario Type',
    'Priority',
    'Test Account Profile',
    'Primary App Tag',
    'Verification Required (HLV/LLV/NA)',
    'KB Trigger Eligible',
    'Expected Agents Path',
    'Initial User Utterance',
    'Full Simulated Conversation',
    'Expected Tools & Flow',
    'Pass Criteria',
    'Tester Status',
    'Tester Notes'
]

QA_COL_WIDTHS = [16, 26, 36, 16, 12, 38, 24, 18, 12, 42, 38, 75, 34, 42, 18, 28]


def escape_xml_val(s: Any) -> str:
    """Escape XML characters while preserving clean string representation."""
    if s is None:
        return ""
    val_str = str(s)
    return saxutils.escape(val_str)


def sanitize_sheet_name(name: str) -> str:
    """Ensure sheet names comply with Excel constraints (<= 31 chars, no forbidden chars)."""
    clean = re_replace_forbidden(name)
    return clean[:31] if len(clean) > 31 else clean


def re_replace_forbidden(s: str) -> str:
    for ch in [':', '\\', '/', '?', '*', '[', ']']:
        s = s.replace(ch, ' ')
    return s.strip()


def num_to_col_letter(n: int) -> str:
    """Convert 1-based column index to Excel column letter(s) (A, B, ..., Z, AA, ...)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def build_overview_rows(suite_tier: str, app_title: str, timestamp: str, subagent_summaries: List[Dict[str, Any]], all_rows: List[List[str]]) -> List[List[str]]:
    """Build the Executive Overview & Tester Instructions sheet."""
    total_tests = len(all_rows)
    overview = [
        [f"{app_title} — {suite_tier.capitalize()} Manual QA Testing Suite"],
        [f"Generated: {timestamp} | Total Test Cases: {total_tests} | Engine: Project CHIME"],
        [""],
        ["1. Purpose & Strategic Scope"],
        ["This manual QA testing workbook provides standardized, turn-by-turn verification test cases for conversational agents across Voice and Chat."],
        [f"The {suite_tier.capitalize()} suite enables zero-context QA testers to immediately evaluate agent behavior across telephony calls or digital chat."],
        [""],
        ["2. Manual QA Execution Guidelines by Channel"],
        ["Channel / Verification Step", "Execution Instructions & Tester Checklist"],
        ["Voice Testing (Telephony / IVR)", "Dial the test telephony number. Use the credentials in 'Test Account Profile' (CLI phone, postcode, password). When greeted, speak 'Initial User Utterance'. Follow 'Full Simulated Conversation'. Verify prompt naturalness, steering, and audio clarity."],
        ["Digital Chat Testing", "Open the CXAS web or mobile chat interface. Use the session profile in 'Test Account Profile'. Enter 'Initial User Utterance'. Continue replying with indicated customer turns. Confirm intent classification and context updates."],
        ["Security Verification (HLV / LLV)", "When 'Verification Required' is HLV or LLV, verify that the assistant prompts the customer for security credentials (e.g. PIN, DOB) BEFORE answering sensitive inquiries or modifying services."],
        ["Pass / Fail Criteria Logging", "Mark [X] PASS in 'Tester Status' if all expectations in 'Pass Criteria' and 'Expected Tools & Flow' are met. If any failure occurs, mark [X] FAIL and record failure details in 'Tester Notes'."],
        [""],
        ["3. Sub-Agent Journey Suite Breakdown"],
        ["Sub-Agent Journey", "Sub-Agent Key", "Total Tests", "Happy Paths", "Non-Happy / Fallbacks", "Escalations", "Guardrails"]
    ]

    total_hp = 0
    total_nh_fb = 0
    total_esc = 0
    total_guard = 0

    for summary in subagent_summaries:
        j_key = summary['key']
        j_label = summary['domain_label']
        j_rows = [r for r in all_rows if r[1] == j_label]
        hp = sum(1 for r in j_rows if len(r) > 3 and r[3] == 'Happy Path')
        nh_fb = sum(1 for r in j_rows if len(r) > 3 and r[3] in ['Non-Happy Path', 'Edge', 'Fallback'])
        esc = sum(1 for r in j_rows if len(r) > 3 and r[3] == 'Escalation')
        guard = sum(1 for r in j_rows if len(r) > 3 and r[3] == 'Guardrail')
        total_hp += hp
        total_nh_fb += nh_fb
        total_esc += esc
        total_guard += guard
        overview.append([j_label, j_key, str(len(j_rows)), str(hp), str(nh_fb), str(esc), str(guard)])

    overview.append([f"Total Across All {len(subagent_summaries)} Journey(s)", "All", str(total_tests), str(total_hp), str(total_nh_fb), str(total_esc), str(total_guard)])
    return overview


def generate_manual_qa_excel_suite(output_xlsx_path: str, suite_tier: str, app_title: str, timestamp: str, sheets_dict: Dict[str, List[List[str]]], col_widths: List[int] = None):
    """Generate multi-tab OpenXML .xlsx manual QA testing workbook with full Google Sheets and Excel compatibility."""
    os.makedirs(os.path.dirname(os.path.abspath(output_xlsx_path)), exist_ok=True)
    
    sst_list: List[str] = []
    sst_map: Dict[str, int] = {}
    total_string_refs = 0

    def get_sst_idx(val: Any) -> Optional[int]:
        nonlocal total_string_refs
        if val is None:
            return None
        val_str = str(val)
        if val_str == "":
            return None
        total_string_refs += 1
        if val_str not in sst_map:
            idx = len(sst_list)
            sst_map[val_str] = idx
            sst_list.append(val_str)
            return idx
        return sst_map[val_str]

    clean_sheets = {sanitize_sheet_name(k): v for k, v in sheets_dict.items()}
    num_sheets = len(clean_sheets)

    with zipfile.ZipFile(output_xlsx_path, 'w', zipfile.ZIP_DEFLATED) as z:
        # [Content_Types].xml
        ct = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">',
              '  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>',
              '  <Default Extension="xml" ContentType="application/xml"/>',
              '  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>',
              '  <Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>',
              '  <Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>']
        for i in range(1, num_sheets + 1):
            ct.append(f'  <Override PartName="/xl/worksheets/sheet{i}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')
        ct.append('</Types>')
        z.writestr('[Content_Types].xml', '\n'.join(ct))

        # _rels/.rels
        rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">',
                '  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>',
                '</Relationships>']
        z.writestr('_rels/.rels', '\n'.join(rels))

        # xl/_rels/workbook.xml.rels
        wb_rels = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">']
        for i in range(1, num_sheets + 1):
            wb_rels.append(f'  <Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{i}.xml"/>')
        wb_rels.append(f'  <Relationship Id="rId{num_sheets + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>')
        wb_rels.append(f'  <Relationship Id="rId{num_sheets + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>')
        wb_rels.append('</Relationships>')
        z.writestr('xl/_rels/workbook.xml.rels', '\n'.join(wb_rels))

        # xl/workbook.xml
        wb = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
              '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
              '  <workbookPr date1904="false"/>',
              '  <bookViews><workbookView xWindow="0" yWindow="0" windowWidth="25600" windowHeight="14400"/></bookViews>',
              '  <sheets>']
        for i, s_name in enumerate(clean_sheets.keys(), 1):
            wb.append(f'    <sheet name="{escape_xml_val(s_name)}" sheetId="{i}" r:id="rId{i}"/>')
        wb.append('  </sheets>')
        wb.append('</workbook>')
        z.writestr('xl/workbook.xml', '\n'.join(wb))

        # xl/styles.xml
        styles = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <fonts count="4">
    <font><sz val="10"/><name val="Arial"/></font>
    <font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Arial"/></font>
    <font><b/><sz val="10"/><color rgb="FF1E293B"/><name val="Arial"/></font>
    <font><b/><sz val="14"/><color rgb="FF1E3A8A"/><name val="Arial"/></font>
  </fonts>
  <fills count="4">
    <fill><patternFill patternType="none"/></fill>
    <fill><patternFill patternType="gray125"/></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FF1E293B"/></patternFill></fill>
    <fill><patternFill patternType="solid"><fgColor rgb="FFF1F5F9"/></fgColor></patternFill></fill>
  </fills>
  <borders count="2">
    <border><left/><right/><top/><bottom/><diagonal/></border>
    <border>
      <left style="thin"><color rgb="FFE2E8F0"/></left>
      <right style="thin"><color rgb="FFE2E8F0"/></right>
      <top style="thin"><color rgb="FFE2E8F0"/></top>
      <bottom style="thin"><color rgb="FFE2E8F0"/></bottom>
    </border>
  </borders>
  <cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
  <cellXfs count="5">
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
    <xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="center"/></xf>
    <xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="top"/></xf>
  </cellXfs>
</styleSheet>'''
        z.writestr('xl/styles.xml', styles)

        # Worksheets
        for sheet_idx, (s_name, rows) in enumerate(clean_sheets.items(), 1):
            sheet_xml_parts = [
                '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
                '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">',
                '  <sheetViews><sheetView tabSelected="' + ('1' if sheet_idx == 1 else '0') + '" workbookViewId="0">',
                '    <pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/>',
                '  </sheetView></sheetViews>',
                '  <sheetFormatPr defaultRowHeight="20"/>'
            ]

            # Columns definition
            widths = col_widths or QA_COL_WIDTHS
            sheet_xml_parts.append('  <cols>')
            for c_idx, w in enumerate(widths, 1):
                sheet_xml_parts.append(f'    <col min="{c_idx}" max="{c_idx}" width="{w}" customWidth="1"/>')
            sheet_xml_parts.append('  </cols>')

            # Sheet Data
            sheet_xml_parts.append('  <sheetData>')
            for r_idx, row in enumerate(rows, 1):
                is_header = (r_idx == 1)
                is_title = (r_idx == 1 and s_name.lower().startswith('overview'))
                row_h = 32 if is_header else 24

                sheet_xml_parts.append(f'    <row r="{r_idx}" ht="{row_h}" customHeight="1">')
                for c_idx, cell_val in enumerate(row, 1):
                    col_let = num_to_col_letter(c_idx)
                    cell_ref = f"{col_let}{r_idx}"
                    
                    if is_title and c_idx == 1:
                        style_idx = 3
                    elif is_header:
                        style_idx = 1
                    else:
                        style_idx = 0

                    if cell_val is not None and str(cell_val).strip() != "":
                        sst_i = get_sst_idx(cell_val)
                        sheet_xml_parts.append(f'      <c r="{cell_ref}" s="{style_idx}" t="s"><v>{sst_i}</v></c>')
                    else:
                        sheet_xml_parts.append(f'      <c r="{cell_ref}" s="{style_idx}"/>')
                sheet_xml_parts.append('    </row>')
            sheet_xml_parts.append('  </sheetData>')
            sheet_xml_parts.append('</worksheet>')

            z.writestr(f'xl/worksheets/sheet{sheet_idx}.xml', '\n'.join(sheet_xml_parts))

        # xl/sharedStrings.xml
        sst_xml = [
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
            f'<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{total_string_refs}" uniqueCount="{len(sst_list)}">'
        ]
        for s in sst_list:
            sst_xml.append(f'  <si><t>{escape_xml_val(s)}</t></si>')
        sst_xml.append('</sst>')
        z.writestr('xl/sharedStrings.xml', '\n'.join(sst_xml))
