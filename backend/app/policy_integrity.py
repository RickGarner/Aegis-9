"""Local signature verification and drift status for governed policy artifacts."""
import base64
import hashlib
from pathlib import Path
from cryptography.hazmat.primitives.serialization import load_pem_public_key

class PolicyIntegrityError(RuntimeError): pass

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

def resolve_policy_path(path: Path) -> Path:
    """Resolve configured policy paths consistently, independent of process CWD."""
    return path if path.is_absolute() else (REPOSITORY_ROOT / path).resolve()

def verify_policy(path: Path, public_key_path: Path) -> bool:
    path = resolve_policy_path(path)
    public_key_path = resolve_policy_path(public_key_path)
    signature_path = Path(f"{path}.sig")
    if not path.is_file() or not signature_path.is_file() or not public_key_path.is_file(): return False
    try:
        key = load_pem_public_key(public_key_path.read_bytes())
        key.verify(base64.b64decode(signature_path.read_text(encoding="utf-8").strip(), validate=True), path.read_bytes())
        return True
    except Exception: return False

def policy_status(paths: list[Path], *, required: bool, public_key_path: Path) -> dict:
    public_key_path = resolve_policy_path(public_key_path)
    artifacts = []
    for path in paths:
        path = resolve_policy_path(path)
        signed = Path(f"{path}.sig").is_file()
        valid = verify_policy(path, public_key_path) if signed else False
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        artifacts.append({"path": str(path), "sha256": digest, "signed": signed, "valid": valid, "drift": required and not valid})
    healthy = all(not item["drift"] for item in artifacts)
    return {"status": "healthy" if healthy else "misconfigured", "signatureRequired": required, "driftDetected": not healthy, "artifacts": artifacts}

def require_policy(path: Path, *, required: bool, public_key_path: Path) -> None:
    path = resolve_policy_path(path)
    public_key_path = resolve_policy_path(public_key_path)
    if required and not verify_policy(path, public_key_path): raise PolicyIntegrityError(f"Signed policy verification failed: {path}")
