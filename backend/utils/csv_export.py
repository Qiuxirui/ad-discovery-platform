"""CSV 导出：UTF-8 BOM + RFC5987 中文文件名（Excel 打开不乱码）。"""

from __future__ import annotations

import csv
import io
from urllib.parse import quote

from starlette.responses import Response

__all__ = ["csv_response"]


def csv_response(rows: list[list[object]], header: list[str], filename: str) -> Response:
    """构造 ``text/csv`` 响应（BOM + 中文文件名）。"""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow(["" if cell is None else cell for cell in row])

    content = "\ufeff" + buffer.getvalue()
    ascii_name = "export.csv"
    disposition = f"attachment; filename={ascii_name}; filename*=UTF-8''{quote(filename)}"
    return Response(
        content=content.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": disposition},
    )
