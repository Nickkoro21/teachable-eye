"""Self-signed HTTPS certificate for the LAN (phone camera/mic need HTTPS).

Adapted from https-deeplearning-ai/sc-on-device-ai-memory, robot/device/server.py
`lan_ip` / `ensure_cert` (Apache-2.0). Changed: stored under data/cert, CN name.
"""
import ipaddress
import socket
from datetime import UTC, datetime, timedelta

from teachable_eye import config


def lan_ip():
    """LAN IP via a dummy UDP connect (no packets sent). Loopback on failure.

    On Windows this can pick a Hyper-V/WSL adapter; pass --advertise then.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def ensure_cert(ip, root=None):
    """Create or reuse a CA-flagged self-signed cert for `ip` + localhost."""
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    root = root or config.DATA_DIR / "cert"
    cert, key, named = root / "cert.pem", root / "key.pem", root / "names.txt"
    hostname = socket.gethostname().split(".")[0] + ".local"
    want = ",".join([f"IP:{ip}", "IP:127.0.0.1", "DNS:localhost",
                     f"DNS:{hostname}"])
    if (cert.exists() and key.exists() and named.exists()
            and named.read_text(encoding="utf-8") == want):
        return cert, key
    root.mkdir(parents=True, exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME,
                                            "teachable-eye local")])
    now = datetime.now(UTC)
    san = x509.SubjectAlternativeName([
        x509.IPAddress(ipaddress.ip_address(ip)),
        x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
        x509.DNSName("localhost"),
        x509.DNSName(hostname),
    ])
    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject).issuer_name(subject)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=397))
        # a phone installs it as a CA, so it may sign nothing else: no
        # sub-CAs, and only this server's own names (security review 2026-10-17)
        .add_extension(x509.BasicConstraints(ca=True, path_length=0),
                       critical=True)
        .add_extension(x509.NameConstraints(permitted_subtrees=[
            x509.IPAddress(ipaddress.ip_network(f"{ip}/32")),
            x509.IPAddress(ipaddress.ip_network("127.0.0.1/32")),
            x509.DNSName("localhost"), x509.DNSName(hostname)],
            excluded_subtrees=None), critical=True)
        .add_extension(san, critical=False)
        .sign(private_key, hashes.SHA256())
    )
    key.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption()))
    cert.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    named.write_text(want, encoding="utf-8")
    print(f"generated a certificate for {ip} (valid 397 days)")
    return cert, key
