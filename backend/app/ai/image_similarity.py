"""Image similarity abstraction.

`calculate_image_similarity(image_a, image_b)` is the single entry point. The MVP
uses perceptual hashes: real ones when Pillow+imagehash are installed and the image
is fetchable, otherwise the hash supplied with the listing (the mock adapters ship a
simulated pHash). A CLIP / SigLIP provider can be dropped in by implementing
`ImageSimilarityProvider.similarity`.
"""
from dataclasses import dataclass
from app.config import get_settings


@dataclass
class ImageRef:
    url: str
    phash: str = ""   # 16-hex-char (64-bit) perceptual hash, may be empty


class ImageSimilarityProvider:
    name = "base"

    def similarity(self, a: ImageRef, b: ImageRef) -> float:
        raise NotImplementedError


def hamming_similarity(h1: str, h2: str) -> float:
    if not h1 or not h2:
        return 0.5   # unknown — neutral
    x = int(h1, 16) ^ int(h2, 16)
    return 1.0 - bin(x).count("1") / 64.0


class PerceptualHashProvider(ImageSimilarityProvider):
    """Uses precomputed perceptual hashes; computes them from the image when possible."""
    name = "placeholder"

    def _hash(self, ref: ImageRef) -> str:
        if ref.phash:
            return ref.phash
        try:  # optional real pHash path
            import imagehash, requests  # type: ignore
            from PIL import Image  # type: ignore
            from io import BytesIO
            img = Image.open(BytesIO(requests.get(ref.url, timeout=5).content))
            return str(imagehash.phash(img))
        except Exception:
            return ""

    def similarity(self, a: ImageRef, b: ImageRef) -> float:
        return hamming_similarity(self._hash(a), self._hash(b))


class CLIPImageSimilarityProvider(ImageSimilarityProvider):
    """Stub: embed both images with a vision model and return cosine similarity."""
    name = "clip"

    def similarity(self, a: ImageRef, b: ImageRef) -> float:
        raise NotImplementedError("Install a CLIP/SigLIP backend and implement embed+cosine here")


_provider: ImageSimilarityProvider | None = None


def get_image_provider() -> ImageSimilarityProvider:
    global _provider
    if _provider is None:
        name = get_settings().image_similarity_provider
        _provider = CLIPImageSimilarityProvider() if name == "clip" else PerceptualHashProvider()
    return _provider


def calculate_image_similarity(image_a: ImageRef, image_b: ImageRef) -> float:
    return round(get_image_provider().similarity(image_a, image_b), 4)
