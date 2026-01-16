"""
Device authentication using RSA-2048 signatures.
DerbyPi devices authenticate by signing requests with their private key.
"""
import base64
import hashlib
import json
import time
from typing import Any

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from app.config import get_settings
from app.redis_client import NonceStore


settings = get_settings()


class DeviceSignatureError(Exception):
    """Device signature verification failed."""
    pass


def generate_keypair() -> tuple[str, str]:
    """
    Generate an RSA-2048 keypair for a device.
    This would be run on the DerbyPi device itself.

    Returns:
        Tuple of (private_key_pem, public_key_pem)
    """
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return private_pem, public_pem


def sign_request(
    private_key_pem: str,
    device_id: str,
    method: str,
    path: str,
    body: bytes | None = None,
    timestamp: int | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    """
    Sign an API request with the device's private key.
    This would be called on the DerbyPi device.

    Args:
        private_key_pem: PEM-encoded private key
        device_id: Device identifier
        method: HTTP method (GET, POST, etc.)
        path: Request path
        body: Request body (optional)
        timestamp: Unix timestamp (defaults to now)
        nonce: Unique nonce (defaults to generated)

    Returns:
        Dict of headers to include in the request:
        - X-Device-Id
        - X-Timestamp
        - X-Nonce
        - X-Signature
    """
    import secrets

    if timestamp is None:
        timestamp = int(time.time())
    if nonce is None:
        nonce = secrets.token_urlsafe(12)

    # Compute body hash
    if body:
        body_hash = f"sha256:{hashlib.sha256(body).hexdigest()}"
    else:
        body_hash = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"  # SHA256 of empty string

    # Build canonical payload
    payload = {
        "deviceId": device_id,
        "timestamp": timestamp,
        "nonce": nonce,
        "method": method.upper(),
        "path": path,
        "bodyHash": body_hash,
    }

    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

    # Load private key and sign
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )

    signature = private_key.sign(
        payload_bytes,
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    return {
        "X-Device-Id": device_id,
        "X-Timestamp": str(timestamp),
        "X-Nonce": nonce,
        "X-Signature": base64.b64encode(signature).decode("utf-8"),
    }


async def verify_device_signature(
    public_key_pem: str,
    device_id: str,
    timestamp: int,
    nonce: str,
    signature_b64: str,
    method: str,
    path: str,
    body: bytes | None = None,
) -> bool:
    """
    Verify a device's request signature.

    Args:
        public_key_pem: PEM-encoded public key from database
        device_id: Device identifier from header
        timestamp: Unix timestamp from header
        nonce: Nonce from header
        signature_b64: Base64-encoded signature from header
        method: HTTP method
        path: Request path
        body: Request body

    Returns:
        True if signature is valid

    Raises:
        DeviceSignatureError: If verification fails
    """
    # Check timestamp is within allowed window
    current_time = int(time.time())
    time_diff = abs(current_time - timestamp)

    if time_diff > settings.device_signature_max_age_seconds:
        raise DeviceSignatureError(
            f"Timestamp too old or in future: {time_diff}s difference"
        )

    # Check nonce hasn't been used (replay protection)
    is_new_nonce = await NonceStore.check_and_store(device_id, nonce)
    if not is_new_nonce:
        raise DeviceSignatureError("Nonce already used (replay attack detected)")

    # Compute body hash
    if body:
        body_hash = f"sha256:{hashlib.sha256(body).hexdigest()}"
    else:
        body_hash = "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

    # Rebuild canonical payload
    payload = {
        "deviceId": device_id,
        "timestamp": timestamp,
        "nonce": nonce,
        "method": method.upper(),
        "path": path,
        "bodyHash": body_hash,
    }

    payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")

    # Load public key
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8"),
            backend=default_backend(),
        )
    except Exception as e:
        raise DeviceSignatureError(f"Invalid public key: {e}")

    # Decode signature
    try:
        signature = base64.b64decode(signature_b64)
    except Exception:
        raise DeviceSignatureError("Invalid signature encoding")

    # Verify signature
    try:
        public_key.verify(
            signature,
            payload_bytes,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return True
    except InvalidSignature:
        raise DeviceSignatureError("Invalid signature")
    except Exception as e:
        raise DeviceSignatureError(f"Signature verification failed: {e}")


def validate_public_key(public_key_pem: str) -> bool:
    """
    Validate that a public key is a valid RSA-2048 key.

    Args:
        public_key_pem: PEM-encoded public key

    Returns:
        True if valid RSA-2048 key

    Raises:
        ValueError: If key is invalid
    """
    try:
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode("utf-8"),
            backend=default_backend(),
        )

        # Check key size
        if public_key.key_size < 2048:
            raise ValueError(f"Key size too small: {public_key.key_size} bits (minimum 2048)")

        return True
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Invalid public key format: {e}")
