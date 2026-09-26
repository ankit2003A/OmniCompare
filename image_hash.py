"""Real perceptual hashes (64-bit dHash) for live product thumbnails — Pillow only."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
import httpx


def dhash(data: bytes) -> str:
    from PIL import Image
    img = Image.open(BytesIO(data)).convert("L").resize((9, 8), Image.LANCZOS)
    px = list(img.getdata())
    bits = 0
    for row in range(8):
        for col in range(8):
            bits = (bits << 1) | (px[row * 9 + col] > px[row * 9 + col + 1])
    return f"{bits:016x}"


def _one(client: httpx.Client, url: str) -> str:
    if not url:
        return ""
    try:
        r = client.get(url, timeout=6, follow_redirects=True)
        return dhash(r.content) if r.status_code == 200 else ""
    except Exception:
        return ""


def hash_images(urls: list[str]) -> list[str]:
    with httpx.Client(headers={"User-Agent": "Mozilla/5.0 OmniCompare"}) as client, ThreadPoolExecutor(12) as pool:
        return list(pool.map(lambda u: _one(client, u), urls))
