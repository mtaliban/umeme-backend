"""Excel export helper using openpyxl."""
from __future__ import annotations

from io import BytesIO
from typing import Any

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment


def export_to_xlsx(items: list[dict[str, Any]], columns: list[str]) -> BytesIO:
    """Return a BytesIO containing an XLSX workbook with *columns* as headers."""
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Export"

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="0B3D91")
    header_align = Alignment(horizontal="center", vertical="center")

    # Write headers
    for col_idx, col_name in enumerate(columns, start=1):
        cell = ws.cell(row=1, column=col_idx, value=col_name)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    # Write data rows
    for row_idx, item in enumerate(items, start=2):
        for col_idx, col_name in enumerate(columns, start=1):
            value = item.get(col_name, "")
            if hasattr(value, "isoformat"):
                value = value.isoformat()
            elif not isinstance(value, (str, int, float, bool, type(None))):
                value = str(value)
            ws.cell(row=row_idx, column=col_idx, value=value)

    # Auto-width columns
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 50)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf
