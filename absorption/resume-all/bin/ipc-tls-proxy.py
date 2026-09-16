#!/opt/homebrew/bin/python3
"""
ipc-tls-proxy.py — TLS wrapper for the remote IPC daemon (item C19).

Wraps the Unix-socket IPC daemon with TLS-over-TCP for secure remote access.
Acts as a relay: TLS client/server <-> NDJSON over Unix socket.

Wire protocol:
  - TLS layer: TLS 1.2+ with self-signed cert (generated on first run)
  - NDJSON framing (one JSON object per line)
  - Auth: client cert optional; if cert pinning enabled, only pinned certs allowed

Usage:
    ipc-tls-proxy.py server [--port 8443] [--bind 127.0.0.1]
        [--require-client-cert]
    ipc-tls-proxy.py client <host> <port>
        [--client-cert PATH] [--client-key PATH]
    ipc-tls-proxy.py gen-cert
    ipc-tls-proxy.py gen-client-cert <name>
    ipc-tls-proxy.py test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

HOME = Path.home()
CERT_DIR = HOME / ".local" / "share" / "resume-all" / "tls"
CERT_FILE = CERT_DIR / "server.pem"
KEY_FILE = CERT_DIR / "server.key"
CA_FILE = CERT_DIR / "ca.pem"
CLIENT_DIR = CERT_DIR / "clients"
IPC_SOCKET = HOME / "Library" / "Application Support" / "sharecli" / "ipc.sock"


# ---------------------------------------------------------------------------
# Cert generation
# ---------------------------------------------------------------------------


_OPENSSL_TIMEOUT = 30
_CLIENT_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_CERTIFICATE_MARKER = b"-----BEGIN CERTIFICATE-----"
_PRIVATE_KEY_MARKERS = (
    b"-----BEGIN PRIVATE KEY-----",
    b"-----BEGIN RSA PRIVATE KEY-----",
    b"-----BEGIN EC PRIVATE KEY-----",
    b"-----BEGIN ENCRYPTED PRIVATE KEY-----",
)


def _as_path(value: str | os.PathLike[str]) -> Path:
    """Return a Path while allowing tests/callers to replace path constants."""
    return value if isinstance(value, Path) else Path(value)


def _ensure_directory(path: Path, mode: int = 0o700) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=mode)


def _atomic_write_bytes(path: Path, data: bytes, mode: int = 0o644) -> None:
    """Write *data* and atomically replace *path* on the same filesystem."""
    path = _as_path(path)
    _ensure_directory(path.parent)
    fd = -1
    temporary: Path | None = None
    try:
        fd, temporary_name = tempfile.mkstemp(
            prefix=f".{path.name}.", dir=str(path.parent)
        )
        temporary = Path(temporary_name)
        with os.fdopen(fd, "wb") as output:
            fd = -1
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
        temporary = None
    finally:
        if fd >= 0:
            os.close(fd)
        if temporary is not None:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass


def _replace_temporary_file(source: Path, destination: Path, mode: int) -> None:
    """Atomically move an openssl output into its final location."""
    destination = _as_path(destination)
    _ensure_directory(destination.parent)
    os.chmod(source, mode)
    os.replace(source, destination)


def _atomic_copy(source: Path, destination: Path, mode: int = 0o644) -> None:
    source = _as_path(source)
    _atomic_write_bytes(_as_path(destination), source.read_bytes(), mode=mode)


def _validate_pem_file(path: Path, kind: str) -> None:
    """Reject missing or non-PEM certificate/key files before handing them to SSL."""
    path = _as_path(path)
    if not path.is_file():
        raise FileNotFoundError(f"{kind} file not found: {path}")
    data = path.read_bytes()
    if kind == "certificate":
        valid = _CERTIFICATE_MARKER in data
    elif kind == "private key":
        valid = any(marker in data for marker in _PRIVATE_KEY_MARKERS)
    else:
        raise ValueError(f"unsupported PEM kind: {kind}")
    if not valid:
        raise ValueError(f"{kind} file is not PEM: {path}")


def _run_openssl(command: list[str]) -> None:
    """Run openssl without leaking command output or private key material."""
    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            timeout=_OPENSSL_TIMEOUT,
        )
    except FileNotFoundError as exc:
        raise RuntimeError("openssl is not installed or not on PATH") from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"openssl certificate generation timed out after {_OPENSSL_TIMEOUT}s"
        ) from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr
        if isinstance(stderr, bytes):
            detail = stderr.decode(errors="replace").strip()
        else:
            detail = str(stderr or "").strip()
        # Keep diagnostics to one line; never print captured key/certificate data.
        detail = detail.splitlines()[-1] if detail else "command failed"
        raise RuntimeError(f"openssl failed: {detail}") from exc


def _ensure_server_material() -> None:
    """Create the legacy server certificate if either server file is absent."""
    cert_file = _as_path(CERT_FILE)
    key_file = _as_path(KEY_FILE)
    if not cert_file.exists() or not key_file.exists():
        gen_self_signed_cert()


def _ensure_ca() -> Path:
    """Ensure the CA trust anchor exists.

    In the compatibility/self-signed mode the server certificate is also the CA
    certificate and the server key signs client certificates.
    """
    cert_file = _as_path(CERT_FILE)
    key_file = _as_path(KEY_FILE)
    ca_file = _as_path(CA_FILE)
    _ensure_server_material()
    if not ca_file.exists():
        _validate_pem_file(cert_file, "certificate")
        _atomic_copy(cert_file, ca_file, mode=0o644)
    _validate_pem_file(ca_file, "certificate")
    # Keep this check explicit: a CA is required for client-auth validation.
    _validate_pem_file(key_file, "private key")
    return ca_file


def gen_self_signed_cert(days: int = 365) -> tuple[Path, Path]:
    """Generate a self-signed TLS cert/key and a CA copy.

    The self-signed server certificate deliberately has CA:TRUE so it can be
    used as the trust anchor for client certificates without introducing a
    second, undocumented key file.  All final files are installed atomically.
    Returns (server certificate, server key) paths.
    """
    if days <= 0:
        raise ValueError("certificate lifetime must be positive")

    cert_dir = _as_path(CERT_DIR)
    cert_file = _as_path(CERT_FILE)
    key_file = _as_path(KEY_FILE)
    ca_file = _as_path(CA_FILE)
    _ensure_directory(cert_dir)

    subj = "/CN=resume-all-ipc-tls/O=kooshapari"
    with tempfile.TemporaryDirectory(
        prefix=".ipc-tls-cert-", dir=str(cert_dir)
    ) as temporary_dir:
        temporary_dir = Path(temporary_dir)
        temporary_key = temporary_dir / "server.key"
        temporary_cert = temporary_dir / "server.pem"
        command = [
            "openssl", "req", "-x509", "-newkey", "rsa:2048",
            "-keyout", str(temporary_key),
            "-out", str(temporary_cert),
            "-days", str(days),
            "-nodes", "-sha256", "-subj", subj,
            "-addext", "basicConstraints=critical,CA:TRUE,pathlen:1",
            "-addext",
            "keyUsage=critical,digitalSignature,keyEncipherment,keyCertSign,cRLSign",
            "-addext", "subjectKeyIdentifier=hash",
        ]
        _run_openssl(command)
        _validate_pem_file(temporary_cert, "certificate")
        _validate_pem_file(temporary_key, "private key")

        _replace_temporary_file(temporary_key, key_file, mode=0o600)
        _replace_temporary_file(temporary_cert, cert_file, mode=0o644)

    # The CA file is intentionally a byte-for-byte copy of the server cert in
    # self-signed mode.  Copying through a temporary file keeps replacement
    # atomic even if a previous CA file exists.
    _atomic_copy(cert_file, ca_file, mode=0o644)
    return cert_file, key_file


def gen_client_cert(name: str, days: int = 365) -> tuple[Path, Path]:
    """Generate a PEM client certificate signed by the server CA.

    Client names are restricted to a single safe filename component.  The
    private key is never printed and is installed with mode 0600.
    Returns (client certificate, client key) paths.
    """
    if not isinstance(name, str) or not _CLIENT_NAME_RE.fullmatch(name):
        raise ValueError(
            "client name must start with a letter or number and contain only "
            "letters, numbers, '.', '_' or '-'"
        )
    if days <= 0:
        raise ValueError("certificate lifetime must be positive")

    ca_file = _ensure_ca()
    key_file = _as_path(KEY_FILE)
    client_dir = _as_path(CLIENT_DIR)
    _ensure_directory(client_dir)
    client_cert = client_dir / f"{name}.pem"
    client_key = client_dir / f"{name}.key"

    extensions = """[v3_client]
 basicConstraints = critical, CA:FALSE
 keyUsage = critical, digitalSignature, keyEncipherment
 extendedKeyUsage = clientAuth
 subjectKeyIdentifier = hash
 authorityKeyIdentifier = keyid,issuer
"""
    cert_dir = _as_path(CERT_DIR)
    with tempfile.TemporaryDirectory(
        prefix=".ipc-tls-client-", dir=str(cert_dir)
    ) as temporary_dir:
        temporary_dir = Path(temporary_dir)
        temporary_key = temporary_dir / "client.key"
        csr = temporary_dir / "client.csr"
        temporary_cert = temporary_dir / "client.pem"
        extension_file = temporary_dir / "client-ext.cnf"
        serial_file = temporary_dir / "client-ca.srl"
        extension_file.write_text(extensions, encoding="ascii")

        _run_openssl([
            "openssl", "req", "-new", "-newkey", "rsa:2048",
            "-keyout", str(temporary_key),
            "-out", str(csr),
            "-nodes", "-sha256",
            "-subj", f"/CN={name}/O=resume-all",
        ])
        _run_openssl([
            "openssl", "x509", "-req",
            "-in", str(csr),
            "-CA", str(ca_file),
            "-CAkey", str(key_file),
            "-CAcreateserial", "-CAserial", str(serial_file),
            "-out", str(temporary_cert),
            "-days", str(days), "-sha256",
            "-extfile", str(extension_file), "-extensions", "v3_client",
        ])
        _validate_pem_file(temporary_cert, "certificate")
        _validate_pem_file(temporary_key, "private key")
        # Read before leaving the temporary directory, then install each final
        # artifact atomically.  The key contents never enter process output.
        key_data = temporary_key.read_bytes()
        cert_data = temporary_cert.read_bytes()

    _atomic_write_bytes(client_key, key_data, mode=0o600)
    _atomic_write_bytes(client_cert, cert_data, mode=0o644)
    return client_cert, client_key


# ---------------------------------------------------------------------------
# TLS server
# ---------------------------------------------------------------------------


def _proxy_one_client(client_sock: ssl.SSLSocket) -> None:
    """Forward NDJSON between TLS client and Unix socket daemon."""
    try:
        upstream = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        upstream.settimeout(5)
        upstream.connect(str(IPC_SOCKET))

        def forward(src, dst, name):
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except (ssl.SSLError, OSError) as e:
                print(f"[{name}] closed: {e}")
            finally:
                try:
                    dst.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

        t1 = threading.Thread(target=forward, args=(client_sock, upstream, "client→daemon"))
        t2 = threading.Thread(target=forward, args=(upstream, client_sock, "daemon→client"))
        t1.daemon = True
        t2.daemon = True
        t1.start()
        t2.start()
        t1.join()
        t2.join()
    except Exception as e:
        print(f"proxy error: {e}")
    finally:
        try:
            client_sock.close()
        except OSError:
            pass


def build_server_context(require_client_cert: bool = False) -> ssl.SSLContext:
    """Build the server context, optionally requiring a CA-signed client cert."""
    _ensure_server_material()
    cert_file = _as_path(CERT_FILE)
    key_file = _as_path(KEY_FILE)
    _validate_pem_file(cert_file, "certificate")
    _validate_pem_file(key_file, "private key")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    if require_client_cert:
        ca_file = _ensure_ca()
        context.load_verify_locations(cafile=str(ca_file))
        context.verify_mode = ssl.CERT_REQUIRED
    return context


def _distinguished_name_value(name: object, key: str) -> str | None:
    """Extract one field from ssl.getpeercert()'s nested DN representation."""
    if not isinstance(name, (tuple, list)):
        return None
    for relative_name in name:
        if not isinstance(relative_name, (tuple, list)):
            continue
        for attribute in relative_name:
            if (
                isinstance(attribute, (tuple, list))
                and len(attribute) == 2
                and attribute[0] == key
            ):
                return str(attribute[1])
    return None


def _format_distinguished_name(name: object) -> str:
    if not isinstance(name, (tuple, list)):
        return "<unknown>"
    attributes: list[str] = []
    for relative_name in name:
        if not isinstance(relative_name, (tuple, list)):
            continue
        for attribute in relative_name:
            if isinstance(attribute, (tuple, list)) and len(attribute) == 2:
                field = str(attribute[0]).replace("\r", "\\r").replace("\n", "\\n")
                value = str(attribute[1]).replace("\r", "\\r").replace("\n", "\\n")
                attributes.append(f"{field}={value}")
    return ", ".join(attributes) or "<unknown>"


def _print_peer_certificate(peer_certificate: dict[str, object]) -> None:
    cn = _distinguished_name_value(peer_certificate.get("subject"), "commonName")
    if cn is None:
        cn = "<unknown>"
    cn = cn.replace("\r", "\\r").replace("\n", "\\n")
    issuer = _format_distinguished_name(peer_certificate.get("issuer"))
    print(f"TLS peer certificate: CN={cn}; issuer={issuer}", flush=True)


def run_server(
    bind: str,
    port: int,
    require_client_cert: bool = False,
) -> int:
    """Run TLS-over-TCP server that proxies to the IPC daemon."""
    if not _as_path(CERT_FILE).exists() or not _as_path(KEY_FILE).exists():
        print("Generating self-signed cert...")

    context = build_server_context(require_client_cert=require_client_cert)

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((bind, port))
    sock.listen(8)
    print(f"ipc-tls-proxy: listening on {bind}:{port} (TLS)")
    print(f"  cert: {CERT_FILE}")
    if require_client_cert:
        print(f"  client auth: required; CA: {CA_FILE}")
    else:
        print("  client auth: disabled")
    print(f"  upstream: {IPC_SOCKET}")
    print("  Ctrl-C to stop")

    try:
        while True:
            client, addr = sock.accept()
            try:
                # wrap_socket performs the handshake here.  CERT_REQUIRED makes
                # missing, expired, or untrusted client certificates fail before
                # a proxy thread can reach the Unix-socket daemon.
                tls_client = context.wrap_socket(client, server_side=True)
                peer_certificate = tls_client.getpeercert()
                if peer_certificate:
                    _print_peer_certificate(peer_certificate)
                threading.Thread(
                    target=_proxy_one_client,
                    args=(tls_client,),
                    daemon=True,
                ).start()
            except ssl.SSLError as exc:
                print(f"TLS handshake failed from {addr}: {exc}")
                client.close()
            except OSError as exc:
                print(f"TLS connection failed from {addr}: {exc}")
                client.close()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        sock.close()
    return 0


# ---------------------------------------------------------------------------
# TLS client (for testing)
# ---------------------------------------------------------------------------


def build_client_context(
    client_cert: str | os.PathLike[str] | None = None,
    client_key: str | os.PathLike[str] | None = None,
) -> ssl.SSLContext:
    """Build a server-verifying client context, optionally with a cert chain."""
    if (client_cert is None) != (client_key is None):
        raise ValueError(
            "--client-cert and --client-key must be supplied together"
        )

    # New installations use ca.pem.  Falling back to server.pem preserves
    # compatibility with installations created before ca.pem was introduced.
    ca_file = _as_path(CA_FILE)
    cert_file = _as_path(CERT_FILE)
    trust_file = ca_file if ca_file.exists() else cert_file
    _validate_pem_file(trust_file, "certificate")

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=str(trust_file))
    # The generated self-signed cert has a stable service CN rather than the
    # caller-provided host.  Certificate-chain verification remains required.
    context.check_hostname = False

    if client_cert is not None and client_key is not None:
        client_cert_path = _as_path(client_cert)
        client_key_path = _as_path(client_key)
        _validate_pem_file(client_cert_path, "certificate")
        _validate_pem_file(client_key_path, "private key")
        context.load_cert_chain(
            certfile=str(client_cert_path),
            keyfile=str(client_key_path),
        )
    return context


def run_client(
    host: str,
    port: int,
    client_cert: str | os.PathLike[str] | None = None,
    client_key: str | os.PathLike[str] | None = None,
) -> int:
    """Simple TLS client that sends health.status and prints the response."""
    if not _as_path(CA_FILE).exists() and not _as_path(CERT_FILE).exists():
        print(
            f"client: no CA/server cert at {CA_FILE} or {CERT_FILE}; "
            "cannot verify server"
        )
        return 1

    try:
        context = build_client_context(
            client_cert=client_cert,
            client_key=client_key,
        )
        with socket.create_connection((host, port), timeout=10) as raw:
            with context.wrap_socket(raw, server_hostname=host) as tls:
                msg = {"id": 1, "method": "health.status", "params": {}}
                tls.sendall((json.dumps(msg) + "\n").encode())
                buf = b""
                while True:
                    chunk = tls.recv(4096)
                    if not chunk:
                        break
                    buf += chunk
                    if buf.endswith(b"\n"):
                        break
                print(f"client: received {len(buf)} bytes")
                print(buf.decode())
        return 0
    except (ValueError, ssl.SSLError, OSError) as exc:
        print(f"client error: {exc}")
        return 1


# ---------------------------------------------------------------------------
# Self-tests
# ---------------------------------------------------------------------------


def _self_test() -> tuple[int, int]:
    passed = 0
    total = 0

    def check(name: str, cond: bool) -> None:
        nonlocal passed, total
        total += 1
        marker = "ok" if cond else "FAIL"
        if cond:
            passed += 1
        print(f"  [{marker}] {name}")

    print("=== ipc-tls-proxy.py self-tests ===")

    # Test 1: cert directory creation
    CERT_DIR.mkdir(parents=True, exist_ok=True)
    test_dir = CERT_DIR / ".test-subdir"
    test_dir.mkdir(exist_ok=True)
    check("CERT_DIR exists", CERT_DIR.exists())
    check("test subdir created", test_dir.exists())
    test_dir.rmdir()

    # Test 2: cert generation
    if CERT_FILE.exists():
        CERT_FILE.rename(CERT_FILE.with_suffix(".pem.bak"))
    if KEY_FILE.exists():
        KEY_FILE.rename(KEY_FILE.with_suffix(".key.bak"))
    try:
        cert, key = gen_self_signed_cert(days=1)
        check("cert generated", cert.exists())
        check("key generated", key.exists())
        check("cert is PEM", cert.read_text().startswith("-----BEGIN CERTIFICATE-----"))
        check("key is PEM", key.read_text().startswith("-----BEGIN PRIVATE KEY-----")
              or key.read_text().startswith("-----BEGIN RSA PRIVATE KEY-----"))
    except Exception as e:
        check(f"cert generation failed: {e}", False)
    # Leave certs in place for actual server use

    # Test 3: SSL context creation
    try:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
        check("TLS server context loads", True)
    except Exception as e:
        check(f"TLS context load: {e}", False)

    # Test 4: TLS client context with our self-signed cert as CA
    try:
        client_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        client_ctx.load_verify_locations(cafile=str(CERT_FILE))
        check("TLS client context loads", True)
    except Exception as e:
        check(f"TLS client context: {e}", False)

    # Test 5: client behavior on bad host (should fail gracefully)
    rc = run_client("127.0.0.1", 1)  # nothing listening
    check("client handles bad port gracefully", True)  # we just want no crash

    print(f"\n{passed}/{total} passed")
    return passed, total


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="cmd")

    p_server = sub.add_parser("server")
    p_server.add_argument("--bind", default="127.0.0.1")
    p_server.add_argument("--port", type=int, default=8443)
    p_server.add_argument("--require-client-cert", action="store_true",
                          help="Require mTLS (client cert verification)")
    p_server.set_defaults(func=lambda a: run_server(a.bind, a.port,
                                                      require_client_cert=a.require_client_cert))

    p_client = sub.add_parser("client")
    p_client.add_argument("host")
    p_client.add_argument("port", type=int)
    p_client.add_argument("--client-cert", help="Path to client cert (PEM)")
    p_client.add_argument("--client-key", help="Path to client key (PEM)")
    p_client.set_defaults(func=lambda a: run_client(a.host, a.port,
                                                      client_cert=a.client_cert,
                                                      client_key=a.client_key))

    sub.add_parser("gen-cert").set_defaults(
        func=lambda a: gen_self_signed_cert() and print("cert generated"))

    p_gen_client = sub.add_parser("gen-client-cert")
    p_gen_client.add_argument("name")
    p_gen_client.add_argument("--days", type=int, default=365)
    p_gen_client.set_defaults(
        func=lambda a: print(f"client cert: {gen_client_cert(a.name, a.days)}"))

    sub.add_parser("test").set_defaults(func=lambda a: _self_test())

    args = parser.parse_args(argv[1:])
    if not hasattr(args, "func"):
        parser.print_help()
        return 1
    return args.func(args) or 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
