import base64
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat
from app.policy_integrity import policy_status, verify_policy

def test_signed_policy_detects_drift(tmp_path):
    policy=tmp_path/"policy.json"; policy.write_text('{"safe":true}',encoding="utf-8")
    private=Ed25519PrivateKey.generate(); public=tmp_path/"public.pem"; public.write_bytes(private.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo))
    (tmp_path/"policy.json.sig").write_text(base64.b64encode(private.sign(policy.read_bytes())).decode(),encoding="utf-8")
    assert verify_policy(policy,public)
    policy.write_text('{"safe":false}',encoding="utf-8")
    assert policy_status([policy],required=True,public_key_path=public)["driftDetected"] is True
