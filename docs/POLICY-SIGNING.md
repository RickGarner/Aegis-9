# Governed Policy Signing

A.E.G.I.S.-9 supports detached Ed25519 signatures for the security-control registry, MCP catalog, and shared tool-parity contract. Enforcement is disabled by default for development.

1. Keep the private signing key outside the repository and workstation deployment directory.
2. Place only the public key at `config/policy-signing-public.pem`.
3. Sign approved artifacts from a controlled administration workstation:

```powershell
python scripts/sign_policies.py --private-key D:\Secure\aegis-policy-private.pem
```

4. Distribute each artifact with its adjacent `.sig` file.
5. Set `JARVIS_REQUIRE_SIGNED_POLICIES=true` only after all files and the public key are present.
6. Restart A.E.G.I.S.-9 and confirm Policy Integrity displays `VERIFIED`. `DRIFT` means an artifact is missing, changed, or signed by another key.

Never commit the private key. Updating a governed artifact requires review, a new signature, distribution, and another integrity check.
