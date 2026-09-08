import os

from app.post_acceptance import EncryptedSemanticStore, ReviewHistoryStore, create_cyclonedx, export_migration, import_migration, local_embedding, match_offline_vulnerabilities, scan_dependencies, semantic_similarity


def test_encrypted_semantic_index_is_local_and_clearable(tmp_path):
    store = EncryptedSemanticStore(tmp_path / "index.bin", os.urandom(32))
    vector = local_embedding("PowerShell server health")
    store.save([{"id": "one", "vector": vector, "metadata": {"path": "health.ps1"}}])
    assert store.load()[0]["id"] == "one"
    assert semantic_similarity(vector, local_embedding("PowerShell health")) > 0
    store.clear()
    assert store.load() == []


def test_history_sbom_offline_vulnerability_and_migration(tmp_path):
    history = ReviewHistoryStore(tmp_path / "history.jsonl")
    history.append("review", 1, "passed", False)
    dependencies = scan_dependencies({"requirements.txt": "requests==2.31.0\n", "app.csproj": '<PackageReference Include="Example" Version="1.2.3" />', "package-lock.json": '{"packages":{"node_modules/demo":{"version":"1.0.0","license":"MIT"}}}'})
    vulnerabilities = match_offline_vulnerabilities(dependencies, [{"ecosystem": "pypi", "name": "requests", "version": "2.31.0", "id": "LOCAL-1", "severity": "high", "summary": "fixture"}])
    bundle = tmp_path / "settings.aegis-export"
    export_migration(bundle, {"config/catalog.json": "{}", "secret-token.txt": "no"})
    imported = import_migration(bundle)
    bom = create_cyclonedx(dependencies)
    assert {"history": len(history.list()), "dependencies": len(dependencies), "bom": bom["bomFormat"], "license": next(item for item in bom["components"] if item["name"] == "demo")["licenses"][0]["license"]["id"], "vulnerabilities": len(vulnerabilities), "files": list(imported["files"])} == {"history": 1, "dependencies": 3, "bom": "CycloneDX", "license": "MIT", "vulnerabilities": 1, "files": ["config/catalog.json"]}
