#!/usr/bin/env python3
"""
Generate RSA-2048 keypair for DerbyPi device authentication.
This script is run by Ansible on first boot.
"""
import os
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

# Keys directory - passed from Ansible or use default
KEYS_DIR = os.environ.get('DERBYNET_KEYS_DIR', '/var/lib/derbynet/keys')
PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, 'device.key')
PUBLIC_KEY_PATH = os.path.join(KEYS_DIR, 'device.pub')


def generate_keypair():
    """Generate RSA-2048 keypair and save to files."""
    # Check if keys already exist
    if os.path.exists(PRIVATE_KEY_PATH):
        print(f"Private key already exists at {PRIVATE_KEY_PATH}")
        return 0

    # Ensure directory exists
    os.makedirs(KEYS_DIR, mode=0o700, exist_ok=True)

    # Generate RSA-2048 private key
    print("Generating RSA-2048 keypair...")
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend(),
    )

    # Serialize private key to PEM format
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Serialize public key to PEM format
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    # Write private key (mode 600)
    with open(PRIVATE_KEY_PATH, 'wb') as f:
        f.write(private_pem)
    os.chmod(PRIVATE_KEY_PATH, 0o600)
    print(f"Private key saved to {PRIVATE_KEY_PATH}")

    # Write public key (mode 644)
    with open(PUBLIC_KEY_PATH, 'wb') as f:
        f.write(public_pem)
    os.chmod(PUBLIC_KEY_PATH, 0o644)
    print(f"Public key saved to {PUBLIC_KEY_PATH}")

    # Output public key for registration
    print("\n" + "=" * 60)
    print("PUBLIC KEY FOR SAAS REGISTRATION:")
    print("=" * 60)
    print(public_pem.decode('utf-8'))
    print("=" * 60)

    return 0


if __name__ == '__main__':
    sys.exit(generate_keypair())
