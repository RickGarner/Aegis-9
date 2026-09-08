from app.test_lab import create_test_package, create_test_plan


def test_test_lab_plan_and_package_are_fail_closed(tmp_path):
    plan = create_test_plan({"danger.ps1": "Remove-Item C:\\Data -Recurse; Invoke-RestMethod https://example.test"})
    package = create_test_package(tmp_path, {"danger.ps1": "Remove-Item C:\\Data -Recurse"}, plan)
    assert {"risk": plan["risk"], "network": plan["capabilities"]["network"], "findings": [item["category"] for item in plan["findings"]], "files": sorted(item.name for item in (package / "input").iterdir()), "sandbox": "<Networking>Disable</Networking>" in (package / "AegisTestLab.wsb").read_text()} == {"risk": "critical", "network": False, "findings": ["destructive-filesystem", "network"], "files": ["Run-AegisTestLab.ps1", "danger.ps1", "manifest.json", "synthetic-data.json", "test-plan.json"], "sandbox": True}
