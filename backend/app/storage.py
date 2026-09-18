"""DynamoDB and S3 access for the shoutout board."""
import base64
import json
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.config import Config as BotoConfig

from . import config

_boto_config = BotoConfig(
    region_name=config.AWS_REGION,
    retries={"max_attempts": 3, "mode": "standard"},
    signature_version="s3v4",
    s3={"addressing_style": "virtual"},
)

_session = boto3.session.Session(region_name=config.AWS_REGION)
_dynamodb = _session.resource("dynamodb", config=_boto_config)
_table = _dynamodb.Table(config.TABLE_NAME)

# The endpoint is pinned to the region on purpose. Left to resolve on its own,
# boto3 signs against the global s3.amazonaws.com host and S3 answers presigned
# GETs with TemporaryRedirect, which a browser <img> cannot follow.
_s3 = _session.client(
    "s3",
    region_name=config.AWS_REGION,
    endpoint_url=config.S3_ENDPOINT_URL,
    config=_boto_config,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def encode_cursor(last_key: dict | None) -> str | None:
    if not last_key:
        return None
    raw = json.dumps(last_key, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor: str | None) -> dict | None:
    if not cursor:
        return None
    try:
        raw = base64.urlsafe_b64decode(cursor.encode())
        key = json.loads(raw)
    except (ValueError, TypeError):
        raise ValueError("Invalid cursor.")
    if not isinstance(key, dict) or set(key) != {"board", "posted_at"}:
        raise ValueError("Invalid cursor.")
    return key


def put_image(data: bytes, content_type: str, extension: str) -> str:
    """Store the image privately and return its S3 key."""
    key = f"images/{uuid.uuid4().hex}.{extension}"
    _s3.put_object(
        Bucket=config.BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="public, max-age=31536000, immutable",
    )
    return key


def image_url(key: str | None) -> str | None:
    """Presigned GET so the bucket itself can stay private."""
    if not key:
        return None
    return _s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": config.BUCKET_NAME, "Key": key},
        ExpiresIn=config.PRESIGN_TTL_SECONDS,
    )


def create_shoutout(first_name: str, last_name: str, message: str,
                    image_key: str | None) -> dict:
    created_at = _now_iso()
    shoutout_id = uuid.uuid4().hex
    # Sort key embeds the id so two posts in the same millisecond cannot collide.
    item = {
        "board": config.BOARD_ID,
        "posted_at": f"{created_at}#{shoutout_id}",
        "id": shoutout_id,
        "first_name": first_name,
        "last_name": last_name,
        "message": message,
        "created_at": created_at,
    }
    if image_key:
        item["image_key"] = image_key
    _table.put_item(Item=item)
    return item


def list_shoutouts(limit: int, cursor: str | None) -> tuple[list[dict], str | None]:
    kwargs = {
        "KeyConditionExpression": Key("board").eq(config.BOARD_ID),
        "ScanIndexForward": False,  # newest first
        "Limit": limit,
    }
    start_key = decode_cursor(cursor)
    if start_key:
        kwargs["ExclusiveStartKey"] = start_key
    response = _table.query(**kwargs)
    items = response.get("Items", [])
    return items, encode_cursor(response.get("LastEvaluatedKey"))


def to_public(item: dict) -> dict:
    """Shape a stored item for the API, hiding internal keys."""
    return {
        "id": item.get("id"),
        "first_name": item.get("first_name", ""),
        "last_name": item.get("last_name", ""),
        "message": item.get("message", ""),
        "created_at": item.get("created_at"),
        "image_url": image_url(item.get("image_key")),
    }
