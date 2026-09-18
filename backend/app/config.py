"""Runtime configuration, all overridable by environment variables."""
import os


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, "").strip() or default)
    except ValueError:
        return default


AWS_REGION = os.environ.get("AWS_REGION", "ap-south-1")
TABLE_NAME = os.environ.get("SHOUTOUTS_TABLE", "diva-shoutouts")
BUCKET_NAME = os.environ.get("IMAGES_BUCKET", "")

# Every shoutout shares one partition so the board reads back as a single
# time-ordered feed. Fine at demo scale; shard the key if traffic ever grows.
BOARD_ID = os.environ.get("BOARD_ID", "main")

PRESIGN_TTL_SECONDS = _int("PRESIGN_TTL_SECONDS", 3600)
MAX_IMAGE_BYTES = _int("MAX_IMAGE_BYTES", 5 * 1024 * 1024)

NAME_MAX_LEN = _int("NAME_MAX_LEN", 50)
MESSAGE_MAX_LEN = _int("MESSAGE_MAX_LEN", 500)

PAGE_SIZE_DEFAULT = _int("PAGE_SIZE_DEFAULT", 20)
PAGE_SIZE_MAX = _int("PAGE_SIZE_MAX", 50)

# Anyone may post, so throttle per client IP to blunt casual flooding.
RATE_LIMIT_POSTS = _int("RATE_LIMIT_POSTS", 5)
RATE_LIMIT_WINDOW_SECONDS = _int("RATE_LIMIT_WINDOW_SECONDS", 300)

_origins = os.environ.get("ALLOWED_ORIGINS", "*")
ALLOWED_ORIGINS = [o.strip() for o in _origins.split(",") if o.strip()] or ["*"]
