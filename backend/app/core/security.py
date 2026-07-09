import base64
import hashlib
import hmac
import os
import re

from cryptography.fernet import Fernet

from app.core.config import settings


def _fernet_key_from_secret(secret: str) -> bytes:
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class PiiCipher:
    def __init__(self, secret: str) -> None:
        self._fernet = Fernet(_fernet_key_from_secret(secret))

    def encrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")

    def decrypt(self, value: str | None) -> str | None:
        if value is None:
            return None
        return self._fernet.decrypt(value.encode("utf-8")).decode("utf-8")


pii_cipher = PiiCipher(settings.pii_encryption_key)


def normalize_phone(phone: str) -> str:
    stripped = phone.strip()
    plus = "+" if stripped.startswith("+") else ""
    digits = re.sub(r"\D", "", stripped)
    return f"{plus}{digits}"


def phone_hash(phone: str) -> str:
    normalized = normalize_phone(phone)
    return hmac.new(
        settings.app_secret_key.encode("utf-8"),
        normalized.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def secure_compare(left: str, right: str) -> bool:
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def redact_payload(payload: dict) -> dict:
    sensitive_keys = {
        "patient_name",
        "phone",
        "reason",
        "symptoms",
        "summary",
        "transcript",
        "authorization",
    }
    redacted: dict = {}
    for key, value in payload.items():
        if key.lower() in sensitive_keys:
            redacted[key] = "[REDACTED]"
        elif isinstance(value, dict):
            redacted[key] = redact_payload(value)
        else:
            redacted[key] = value
    return redacted


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256$120000${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, password_hash_value: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = password_hash_value.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    salt = base64.b64decode(salt_b64.encode("utf-8"))
    expected = base64.b64decode(digest_b64.encode("utf-8"))
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    return hmac.compare_digest(actual, expected)

