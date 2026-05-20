"""Validate uploaded announcement images by size and file content."""

import os
import uuid

from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def _detect_image_extension(header):
    if header.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
        return ".webp"
    return None


def validate_announcement_image(file_storage) -> tuple[bool, str]:
    """Return (ok, error_message)."""
    if not file_storage or not file_storage.filename:
        return False, "No file provided"

    max_bytes = current_app.config.get("MAX_ANNOUNCEMENT_IMAGE_BYTES", 2 * 1024 * 1024)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)

    if size <= 0:
        return False, "Empty file"
    if size > max_bytes:
        return False, f"Image must be {max_bytes // (1024 * 1024)} MB or smaller"

    header = file_storage.stream.read(32)
    file_storage.stream.seek(0)

    ext = _detect_image_extension(header)
    if not ext or ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, "File must be a valid PNG, JPEG, or WebP image"

    original_ext = os.path.splitext(file_storage.filename)[1].lower()
    if original_ext and original_ext not in ALLOWED_IMAGE_EXTENSIONS:
        return False, "File extension not allowed"

    return True, ""


def announcement_upload_dir() -> str:
    upload_dir = current_app.config.get("ANNOUNCEMENT_UPLOAD_DIR")
    if not upload_dir:
        upload_dir = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "..",
                "uploads",
                "announcements",
            )
        )
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


def save_announcement_image(file_storage):
    """Save validated image; return (public_url_path, error_message)."""
    ok, err = validate_announcement_image(file_storage)
    if not ok:
        return None, err

    header = file_storage.stream.read(32)
    file_storage.stream.seek(0)
    ext = _detect_image_extension(header)
    filename = f"{uuid.uuid4().hex}{ext}"
    safe_name = secure_filename(filename)
    if safe_name != filename:
        return None, "Invalid filename"

    path = os.path.join(announcement_upload_dir(), safe_name)
    file_storage.save(path)
    return f"/api/announcements/media/{safe_name}", ""
