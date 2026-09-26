"""Generated placeholder product images (SVG) so the demo has no external image dependency.

Real adapters return real marketplace image URLs; this router only serves the seeded
catalog's `/images/<slug>.svg` paths.
"""
import hashlib
import re
from fastapi import APIRouter, Response

router = APIRouter()


def _colours(seed: str) -> tuple[str, str]:
    h = hashlib.md5(seed.encode()).hexdigest()
    hue = int(h[:2], 16) * 360 // 256
    return f"hsl({hue} 35% 92%)", f"hsl({hue} 45% 38%)"


@router.get("/images/{slug}.svg")
def placeholder_image(slug: str, bg: str | None = None, fg: str | None = None):
    text = re.sub(r"[-_]+", " ", slug).strip()[:60]
    auto_bg, auto_fg = _colours(slug)
    bg = f"#{bg}" if bg else auto_bg
    fg = f"#{fg}" if fg else auto_fg
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + 1 > 16 and cur:
            lines.append(cur); cur = w
        else:
            cur = f"{cur} {w}".strip()
    if cur:
        lines.append(cur)
    lines = lines[:3]
    y0 = 300 - (len(lines) - 1) * 26
    tspans = "".join(f'<tspan x="300" y="{y0 + i * 52}">{l}</tspan>' for i, l in enumerate(lines))
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="600" height="600" viewBox="0 0 600 600">
<rect width="600" height="600" rx="32" fill="{bg}"/>
<circle cx="300" cy="300" r="190" fill="{fg}" opacity="0.08"/>
<rect x="150" y="150" width="300" height="300" rx="40" fill="{fg}" opacity="0.10"/>
<text text-anchor="middle" font-family="system-ui, sans-serif" font-size="40" font-weight="700" fill="{fg}">{tspans}</text>
<text x="300" y="560" text-anchor="middle" font-family="system-ui, sans-serif" font-size="18" fill="{fg}" opacity="0.7">demo image</text>
</svg>'''
    return Response(svg, media_type="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})
