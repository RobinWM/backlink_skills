"""Check public image URLs against final local assets; never upload files."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ipaddress
from pathlib import Path
import socket
from urllib.parse import parse_qs, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


def public_url(value):
    if not isinstance(value, str) or not value:
        raise ValueError("each hosted image needs public_url")
    parts = urlsplit(value)
    if (parts.scheme != "https" or not parts.hostname or parts.username or parts.password
            or parts.fragment or any(c.isspace() or c in '<>"\\' for c in value)):
        raise ValueError("public_url must be an anonymous HTTPS image URL")
    if parts.hostname.lower() == "localhost" or parts.hostname.lower().endswith((".local", ".localhost")):
        raise ValueError("public_url cannot point to a local host")
    try:
        address = ipaddress.ip_address(parts.hostname)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ValueError("public_url cannot point to a private address")
    signed = {"expires", "signature", "sig", "token", "api_key", "access_token",
              "authorization", "password", "secret", "x-amz-signature", "x-amz-expires",
              "x-goog-signature", "x-goog-expires"}
    if signed.intersection(k.lower() for k in parse_qs(parts.query)):
        raise ValueError("use a stable public URL, not a signed or temporary access link")
    return value


def image_records(visuals):
    items = list(visuals["assets"])
    if visuals.get("cover_image"):
        items.append(visuals["cover_image"])
    return [{"file": a["file"], "public_url": public_url(a.get("public_url")),
             "sha256": a["sha256"]} for a in items]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("image URL redirects; record the final direct URL")


def verify(records):
    opener = build_opener(NoRedirect())
    checked = []
    for record in records:
        url = public_url(record["public_url"])
        parts = urlsplit(url)
        addresses = socket.getaddrinfo(parts.hostname, parts.port or 443, type=socket.SOCK_STREAM)
        if not addresses or any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError("public image must resolve to public addresses")
        request = Request(url, headers={"User-Agent": "ScalableSEO-ImageCheck/1.0",
                                       "Accept": "image/png,image/jpeg"})
        try:
            with opener.open(request, timeout=20) as response:
                if response.status != 200:
                    raise ValueError("public image did not return HTTP 200")
                kind = response.headers.get_content_type()
                expected = "image/png" if Path(record["file"]).suffix.lower() == ".png" else "image/jpeg"
                if kind != expected:
                    raise ValueError("URL must return the image, not a sharing page or different format")
                data = response.read(32 * 1024 * 1024 + 1)
        except OSError as exc:
            raise ValueError("public image request failed; check hosting access and hotlink settings") from exc
        if len(data) > 32 * 1024 * 1024 or hashlib.sha256(data).hexdigest() != record["sha256"]:
            raise ValueError("hosted image differs from the final local asset")
        checked.append({**record, "content_type": kind})
    return {"checked_at": datetime.now(timezone.utc).isoformat(), "images": checked}


def matching_receipt(receipt, records):
    if not isinstance(receipt, dict) or not receipt.get("checked_at"):
        return False
    images = receipt.get("images")
    return (isinstance(images, list) and len(images) == len(records)
            and all(isinstance(saved, dict)
                    and all(saved.get(k) == record[k] for k in record)
                    for saved, record in zip(images, records)))
