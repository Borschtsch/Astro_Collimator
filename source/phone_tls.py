"""Per-installation local TLS identity; never changes OS or browser trust."""

from datetime import datetime, timedelta, timezone
import ipaddress
from pathlib import Path
import ssl
from threading import Lock

_identity_lock = Lock()

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


def fingerprint(certificate):
    return ":".join(f"{byte:02X}" for byte in certificate.fingerprint(hashes.SHA256()))


def private_file(path, data):
    path.write_bytes(data)
    path.chmod(0o600)


def local_identity(directory, addresses):
    # Rapid source changes cannot generate different roots for one installation.
    with _identity_lock:
        return _local_identity(directory, list(addresses))


def _local_identity(directory, addresses):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    key_path, ca_path = directory / "ca-key.pem", directory / "ca.pem"
    now = datetime.now(timezone.utc)
    if key_path.exists() != ca_path.exists():
        raise ValueError("Local phone identity is incomplete. Photos remain available; restore the identity files or deliberately reset the phone-link folder.")
    if key_path.exists() and ca_path.exists():
        ca_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
        ca = x509.load_pem_x509_certificate(ca_path.read_bytes())
        if ca.not_valid_after_utc < now + timedelta(days=1):
            raise ValueError("Phone certificate expired. Remove the phone-link certificate folder and reconnect.")
        if ca.public_key().public_numbers() != ca_key.public_key().public_numbers():
            raise ValueError("Phone certificate and private key do not match.")
    else:
        ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Advanced Astro Collimator local phone CA")])
        ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
              .public_key(ca_key.public_key()).serial_number(x509.random_serial_number())
              .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=3650))
              .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
              .add_extension(x509.KeyUsage(False, False, False, False, False, True, True, False, False), critical=True)
              .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
              .sign(ca_key, hashes.SHA256()))
        private_file(key_path, ca_key.private_bytes(serialization.Encoding.PEM,
                     serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        ca_path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Advanced Astro Collimator phone link")])
    sans = [x509.DNSName("localhost")]
    sans.extend(x509.IPAddress(ipaddress.ip_address(value)) for value in sorted(set(addresses + ["127.0.0.1"])))
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(ca.subject)
                   .public_key(key.public_key()).serial_number(x509.random_serial_number())
                   .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=90))
                   .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
                   .add_extension(x509.SubjectAlternativeName(sans), critical=False)
                   .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
                   .add_extension(x509.KeyUsage(True, False, True, False, False, False, False, False, False), critical=True)
                   .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
                   .sign(ca_key, hashes.SHA256()))
    cert_path, server_key = directory / "server.pem", directory / "server-key.pem"
    cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM) + ca.public_bytes(serialization.Encoding.PEM))
    private_file(server_key, key.private_bytes(serialization.Encoding.PEM,
                 serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert_path, server_key)
    return context, {"ca_der": ca.public_bytes(serialization.Encoding.DER),
                     "ca_pem": ca.public_bytes(serialization.Encoding.PEM),
                     "ca_sha256": fingerprint(ca), "server_sha256": fingerprint(certificate)}
