"""Shoutout board API.

The board is deliberately open: no accounts, no login. Every writer supplies a
first and last name with each post, and that is all we know about them.
"""
import logging
import time
from collections import defaultdict, deque

from botocore.exceptions import BotoCoreError, ClientError
from fastapi import FastAPI, File, Form, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import config, storage
from .validation import ValidationError, clean_image, clean_message, clean_name

logger = logging.getLogger("shoutouts")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

app = FastAPI(title="Shoutout Board API", version="1.0.0", docs_url="/api/docs",
              openapi_url="/api/openapi.json")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# Single process, single instance -- an in-memory window is enough here. If this
# ever runs on more than one box, move the counter to DynamoDB or Redis.
_post_history: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip.strip()
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # nginx appends the true peer last; earlier entries may be spoofed.
        return forwarded.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def rate_limited(ip: str) -> bool:
    """Check the quota without consuming it.

    Only stored posts count, so someone correcting a typo five times is not
    locked out of the board for the rest of the window.
    """
    now = time.monotonic()
    window = _post_history[ip]
    while window and now - window[0] > config.RATE_LIMIT_WINDOW_SECONDS:
        window.popleft()
    if not window:
        # Drop the empty deque the defaultdict just created; otherwise the map
        # grows one entry per IP that ever touched the endpoint.
        _post_history.pop(ip, None)
    return len(window) >= config.RATE_LIMIT_POSTS


def record_post(ip: str) -> None:
    _post_history[ip].append(time.monotonic())


def error(status: int, message: str, field: str | None = None) -> JSONResponse:
    body: dict = {"error": message}
    if field:
        body["field"] = field
    return JSONResponse(status_code=status, content=body)


@app.get("/api/health")
def health():
    return {"status": "ok", "table": config.TABLE_NAME, "bucket": config.BUCKET_NAME}


@app.get("/api/config")
def public_config():
    """Lets the frontend enforce the same limits without hardcoding them."""
    return {
        "name_max_len": config.NAME_MAX_LEN,
        "message_max_len": config.MESSAGE_MAX_LEN,
        "max_image_bytes": config.MAX_IMAGE_BYTES,
        "allowed_image_types": ["image/jpeg", "image/png", "image/gif", "image/webp"],
    }


@app.get("/api/shoutouts")
def list_shoutouts(
    limit: int = Query(config.PAGE_SIZE_DEFAULT, ge=1, le=config.PAGE_SIZE_MAX),
    cursor: str | None = Query(None),
):
    try:
        items, next_cursor = storage.list_shoutouts(limit, cursor)
    except ValueError as exc:
        return error(400, str(exc), "cursor")
    except (BotoCoreError, ClientError):
        logger.exception("failed to list shoutouts")
        return error(503, "Could not load the board. Please try again.")
    return {
        "shoutouts": [storage.to_public(item) for item in items],
        "next_cursor": next_cursor,
    }


@app.post("/api/shoutouts", status_code=201)
async def create_shoutout(
    request: Request,
    first_name: str = Form(...),
    last_name: str = Form(...),
    message: str = Form(...),
    image: UploadFile | None = File(None),
):
    ip = client_ip(request)
    if rate_limited(ip):
        minutes = max(1, config.RATE_LIMIT_WINDOW_SECONDS // 60)
        return error(
            429,
            f"You have posted {config.RATE_LIMIT_POSTS} shoutouts in the last "
            f"{minutes} minutes. Please wait a little while.",
        )

    try:
        first = clean_name(first_name, "first_name", "First name")
        last = clean_name(last_name, "last_name", "Last name")
        body = clean_message(message)

        image_bytes = None
        if image is not None and image.filename:
            # Read one byte past the limit so oversized files are rejected
            # without holding the whole upload in memory.
            image_bytes = await image.read(config.MAX_IMAGE_BYTES + 1)
        upload = clean_image(image_bytes)
    except ValidationError as exc:
        return error(400, exc.message, exc.field)

    try:
        image_key = None
        if upload:
            image_key = storage.put_image(upload.data, upload.content_type, upload.extension)
        item = storage.create_shoutout(first, last, body, image_key)
    except (BotoCoreError, ClientError):
        logger.exception("failed to save shoutout")
        return error(503, "Could not save your shoutout. Please try again.")

    record_post(ip)
    logger.info("shoutout %s posted by %s %s (image=%s)", item["id"], first, last,
                bool(image_key))
    return storage.to_public(item)
