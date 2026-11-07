"""Minimal multipart/form-data parser - not a dependency, just enough to
read the one file field the master-data upload sends. No framework;
plain boundary-splitting per RFC 2046.
"""
import base64
import re


def parse_single_file(event):
    """Returns (filename, file_bytes) for the first file part found, or
    (None, None) if the event isn't a multipart body with a file part."""
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    content_type = headers.get("content-type", "")
    m = re.search(r"boundary=(.+)$", content_type)
    if not m:
        return None, None
    boundary = m.group(1).strip().strip('"')

    body = event.get("body") or ""
    raw = base64.b64decode(body) if event.get("isBase64Encoded") else body.encode()

    delimiter = ("--" + boundary).encode()
    parts = raw.split(delimiter)
    for part in parts:
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, _, content = part.partition(b"\r\n\r\n")
        headers_text = header_blob.decode(errors="replace")
        fm = re.search(r'filename="([^"]*)"', headers_text)
        if fm and fm.group(1):
            return fm.group(1), content.rstrip(b"\r\n")
    return None, None
