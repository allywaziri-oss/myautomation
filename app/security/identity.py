import pathlib
import uuid
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.hazmat.primitives import serialization
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
import datetime

class Identity:
    """Manage device identity and keys."""

    def __init__(self):
        self.config_dir = pathlib.Path.home() / '.myshare'
        self.config_dir.mkdir(exist_ok=True)
        self.device_id_file = self.config_dir / 'device_id.txt'
        self.private_key_file = self.config_dir / 'private_key.pem'
        self.public_key_file = self.config_dir / 'public_key.pem'
        self.cert_file = self.config_dir / 'cert.pem'
        self.key_file = self.config_dir / 'key.pem'

        # Device ID
        if self.device_id_file.exists():
            with open(self.device_id_file) as f:
                self.device_id = f.read().strip()
        else:
            self.device_id = str(uuid.uuid4())
            with open(self.device_id_file, 'w') as f:
                f.write(self.device_id)

        # Ed25519 keys for signing
        if self.private_key_file.exists():
            with open(self.private_key_file, 'rb') as f:
                self.private_key = serialization.load_pem_private_key(f.read(), password=None)
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            pem = self.private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.private_key_file, 'wb') as f:
                f.write(pem)

        self.public_key = self.private_key.public_key()

        if not self.public_key_file.exists():
            pem = self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(self.public_key_file, 'wb') as f:
                f.write(pem)

        # TLS cert and key (RSA for simplicity)
        if not self.cert_file.exists() or not self.key_file.exists():
            tls_private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
            )
            tls_pem = tls_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(self.key_file, 'wb') as f:
                f.write(tls_pem)

            tls_public_key = tls_private_key.public_key()
            subject = issuer = x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, self.device_id),
            ])
            cert = x509.CertificateBuilder().subject_name(
                subject
            ).issuer_name(
                issuer
            ).public_key(
                tls_public_key
            ).serial_number(
                x509.random_serial_number()
            ).not_valid_before(
                datetime.datetime.utcnow()
            ).not_valid_after(
                datetime.datetime.utcnow() + datetime.timedelta(days=365)
            ).sign(tls_private_key, hashes.SHA256())
            with open(self.cert_file, 'wb') as f:
                f.write(cert.public_bytes(serialization.Encoding.PEM))

    def get_pubkey_fingerprint(self):
        """Get SHA256 fingerprint of the public key."""
        digest = hashes.Hash(hashes.SHA256())
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        digest.update(pem)
        return digest.finalize().hex()