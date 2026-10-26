from email.message import Message
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "skills/blog-writer/scripts/public_images.py"
SPEC = importlib.util.spec_from_file_location("public_images_test", SCRIPT)
H = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(H)


class Response:
    status = 200

    def __init__(self, data, kind):
        self.data = data
        self.headers = Message()
        self.headers["Content-Type"] = kind

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, limit):
        return self.data[:limit]


class PublicImageTests(unittest.TestCase):
    def test_url_must_be_public_stable_https_without_secrets(self):
        for value in (None, "file:///tmp/image.png", "http://example.com/x.png",
                      "https://localhost/x.png", "https://127.0.0.1/x.png",
                      "https://u:secret@example.com/x.png", "https://example.com/x.png?X-Amz-Signature=a",
                      'https://example.com/x.png"><script>', "https://example.com/x.png#fragment"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                H.public_url(value)
        self.assertEqual(H.public_url("https://images.example.com/x.png?v=2"),
                         "https://images.example.com/x.png?v=2")

    def test_anonymous_get_checks_mime_and_final_bytes(self):
        data = b"\x89PNG\r\n\x1a\nexample"
        records = [{"file": "images/01-lead-test.png", "public_url": "https://images.example.com/x.png",
                    "sha256": hashlib.sha256(data).hexdigest()}]
        addresses = [(2, 1, 6, "", ("93.184.216.34", 443))]
        with patch.object(H.socket, "getaddrinfo", return_value=addresses), patch.object(H, "build_opener") as opener:
            opener.return_value.open.return_value = Response(data, "image/png")
            receipt = H.verify(records)
            self.assertTrue(H.matching_receipt(receipt, records))
            request = opener.return_value.open.call_args.args[0]
            self.assertNotIn("Cookie", request.headers)
            self.assertNotIn("Authorization", request.headers)
            opener.return_value.open.return_value = Response(b"<html>share</html>", "text/html")
            with self.assertRaises(ValueError):
                H.verify(records)
            opener.return_value.open.return_value = Response(b"different image", "image/png")
            with self.assertRaises(ValueError):
                H.verify(records)

    def test_private_resolution_and_redirect_are_rejected(self):
        record = {"file": "x.png", "public_url": "https://images.example.com/x.png", "sha256": "a" * 64}
        with patch.object(H.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("10.0.0.1", 443))]):
            with self.assertRaises(ValueError):
                H.verify([record])
        with self.assertRaises(ValueError):
            H.NoRedirect().redirect_request(None, None, 302, "", {}, "https://other.example.com/x.png")

    def test_receipt_cannot_cover_changed_url_or_local_file(self):
        record = {"file": "x.png", "public_url": "https://images.example.com/x.png", "sha256": "a" * 64}
        receipt = {"checked_at": "2026-10-15", "images": [record]}
        self.assertTrue(H.matching_receipt(receipt, [record]))
        for changed in ({**record, "sha256": "b" * 64}, {**record, "public_url": "https://other.example.com/x.png"}):
            self.assertFalse(H.matching_receipt(receipt, [changed]))
