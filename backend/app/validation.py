"""Server-side validation. The React form mirrors these rules, but this is
the authoritative copy -- the API is public and anyone can POST to it directly.
"""
from dataclasses import dataclass

from . import config

# Letters (any script) plus the punctuation that legitimately shows up in names.
NAME_PUNCTUATION = set(" '-.")

IMAGE_SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg", "jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", "png"),
    (b"GIF87a", "image/gif", "gif"),
    (b"GIF89a", "image/gif", "gif"),
)

ALLOWED_IMAGE_TYPES = ("image/jpeg", "image/png", "image/gif", "image/webp")


class ValidationError(Exception):
    """Carries a field name so the frontend can highlight the right input."""

    def __init__(self, field: str, message: str):
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass
class ImageUpload:
    data: bytes
    content_type: str
    extension: str


def clean_name(raw: str | None, field: str, label: str) -> str:
    value = " ".join((raw or "").split())
    if not value:
        raise ValidationError(field, f"{label} is required.")
    if len(value) > config.NAME_MAX_LEN:
        raise ValidationError(
            field, f"{label} must be {config.NAME_MAX_LEN} characters or fewer."
        )
    if not any(ch.isalpha() for ch in value):
        raise ValidationError(field, f"{label} must contain at least one letter.")
    for ch in value:
        if not (ch.isalpha() or ch in NAME_PUNCTUATION):
            raise ValidationError(
                field, f"{label} may only contain letters, spaces, hyphens and apostrophes."
            )
    return value


def clean_message(raw: str | None) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValidationError("message", "Message is required.")
    if len(value) > config.MESSAGE_MAX_LEN:
        raise ValidationError(
            "message", f"Message must be {config.MESSAGE_MAX_LEN} characters or fewer."
        )
    # Normalise line endings and cap runaway blank lines.
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    while "\n\n\n" in value:
        value = value.replace("\n\n\n", "\n\n")
    return value


def sniff_image(data: bytes) -> tuple[str, str]:
    """Return (content_type, extension) from magic bytes, ignoring the
    client-supplied Content-Type, which is trivially spoofed."""
    for signature, content_type, extension in IMAGE_SIGNATURES:
        if data.startswith(signature):
            return content_type, extension
    if len(data) >= 12 and data[0:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp", "webp"
    raise ValidationError(
        "image", "Image must be a JPEG, PNG, GIF or WebP file."
    )


def clean_image(data: bytes | None) -> ImageUpload | None:
    if not data:
        return None
    if len(data) > config.MAX_IMAGE_BYTES:
        limit_mb = config.MAX_IMAGE_BYTES / (1024 * 1024)
        raise ValidationError("image", f"Image must be smaller than {limit_mb:.0f} MB.")
    content_type, extension = sniff_image(data)
    return ImageUpload(data=data, content_type=content_type, extension=extension)
