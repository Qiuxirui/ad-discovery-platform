"""确定性 SVG 封面生成（零素材、零外链，满足 P0-K-05）。

同一 ``(category_slug, title)`` 永远生成同一张图；色板按类别固定，
强调橙（#E8590C）不参与装饰，避免与"广告"角标语义冲突。
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from xml.sax.saxutils import escape

from ..constants import CATEGORY_PALETTES
from ..database import COVERS_DIR

__all__ = ["COVER_URL_PREFIX", "generate_cover_svg", "write_cover_file"]

COVER_URL_PREFIX = "/static/covers"

CATEGORY_NAMES: dict[str, str] = {
    "local-service": "本地生活服务",
    "deals": "优惠与促销",
    "digital": "数码与家电",
    "home": "家居与日用",
    "fashion": "服饰与美妆",
    "sports-pet": "运动户外与宠物",
}

_DEFAULT_PALETTE = ("#1F3A5F", "#3E6D8E", "#EAF0F6")

FONT_STACK = "system-ui, -apple-system, 'Segoe UI', 'Microsoft YaHei', 'PingFang SC', sans-serif"


def _seed(category_slug: str, title: str) -> int:
    digest = hashlib.sha256(f"{category_slug}|{title}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _wrap_title(title: str, per_line: int = 14, max_lines: int = 2) -> list[str]:
    """按字符数折行（中文按字宽，超出截断加省略号）。"""
    clean = (title or "商家推广信息").strip()
    lines: list[str] = []
    for index in range(0, len(clean), per_line):
        lines.append(clean[index : index + per_line])
        if len(lines) >= max_lines:
            break
    if len(clean) > per_line * max_lines:
        lines[-1] = lines[-1][: max(1, per_line - 1)] + "…"
    return lines or ["商家推广信息"]


def generate_cover_svg(title: str, category_slug: str, ad_id: int) -> str:
    """生成 800×450（16:9）的确定性 SVG 封面字符串。"""
    palette = CATEGORY_PALETTES.get(category_slug, _DEFAULT_PALETTE)
    dark, mid, light = palette
    seed = _seed(category_slug, title)
    angle = 15 + seed % 60
    circle_x = 520 + seed % 240
    circle_y = 90 + (seed >> 8) % 120
    circle_r = 90 + (seed >> 16) % 80
    tri_x = 80 + (seed >> 24) % 160
    tri_y = 300 + (seed >> 32) % 90
    tri_size = 70 + (seed >> 40) % 60
    rect_x = 300 + (seed >> 4) % 200
    rect_y = 220 + (seed >> 12) % 100
    rect_w = 140 + (seed >> 20) % 120
    rect_h = 90 + (seed >> 28) % 70
    opacity = 0.10 + ((seed >> 44) % 8) / 100
    category_name = CATEGORY_NAMES.get(category_slug, "商家推广")
    title_lines = _wrap_title(title)
    title_spans = "".join(
        f'<tspan x="64" dy="{0 if index == 0 else 46}">{escape(line)}</tspan>'
        for index, line in enumerate(title_lines)
    )
    badge_text = f"广告 · {escape(category_name)}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450" role="img" aria-label="{escape(title)}">
  <defs>
    <linearGradient id="bg{ad_id}" gradientTransform="rotate({angle})">
      <stop offset="0%" stop-color="{dark}"/>
      <stop offset="100%" stop-color="{mid}"/>
    </linearGradient>
  </defs>
  <rect width="800" height="450" fill="url(#bg{ad_id})"/>
  <circle cx="{circle_x}" cy="{circle_y}" r="{circle_r}" fill="{light}" opacity="{opacity:.2f}"/>
  <polygon points="{tri_x},{tri_y + tri_size} {tri_x + tri_size // 2},{tri_y} {tri_x + tri_size},{tri_y + tri_size}" fill="{light}" opacity="{opacity + 0.05:.2f}"/>
  <rect x="{rect_x}" y="{rect_y}" width="{rect_w}" height="{rect_h}" rx="18" fill="{light}" opacity="{opacity + 0.02:.2f}"/>
  <rect width="800" height="450" fill="#0B1B2B" opacity="0.18"/>
  <text x="64" y="86" font-family="{FONT_STACK}" font-size="20" fill="#DCE6F0" letter-spacing="1">{badge_text}</text>
  <text x="64" y="190" font-family="{FONT_STACK}" font-size="40" font-weight="700" fill="#FFFFFF">{title_spans}</text>
  <text x="64" y="392" font-family="{FONT_STACK}" font-size="18" fill="#DCE6F0" opacity="0.85">商家自主提交 · 平台人工审核</text>
  <rect x="0" y="0" width="800" height="6" fill="{light}" opacity="0.5"/>
</svg>
"""


def write_cover_file(ad_id: int, title: str, category_slug: str, target_dir: Path | None = None) -> str:
    """把封面写入 ``static/covers/ad-{id}.svg``，返回可访问的 Web 路径。"""
    directory = target_dir or COVERS_DIR
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"ad-{ad_id}.svg"
    path.write_text(generate_cover_svg(title, category_slug, ad_id), encoding="utf-8")
    return f"{COVER_URL_PREFIX}/{path.name}"
