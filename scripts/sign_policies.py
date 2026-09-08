"""Create detached Ed25519 signatures for governed A.E.G.I.S.-9 artifacts."""
import argparse
import base64
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = [ROOT / "config/security-control.json", ROOT / "config/mcp/catalog.json", ROOT / "docs/SHARED-TOOL-PARITY-CONTRACT.json"]

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--private-key", required=True, type=Path)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args()
    key = load_pem_private_key(args.private_key.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise TypeError("The policy signing key must be an Ed25519 private key.")
    for path in args.paths or DEFAULTS:
        resolved = path.resolve()
        signature = base64.b64encode(key.sign(resolved.read_bytes())).decode("ascii")
        Path(f"{resolved}.sig").write_text(signature + "\n", encoding="utf-8")
        print(f"Signed {resolved}")

if __name__ == "__main__":
    main()
