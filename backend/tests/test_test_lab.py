from app.test_lab import create_test_package, create_test_plan, launch_sandbox, cleanup_sandbox


def test_test_lab_plan_and_package_are_fail_closed(tmp_path):
    plan = create_test_plan({"danger.ps1": "Remove-Item C:\\Data -Recurse; Invoke-RestMethod https://example.test"})
    package = create_test_package(tmp_path, {"danger.ps1": "Remove-Item C:\\Data -Recurse"}, plan)
    assert {"risk": plan["risk"], "network": plan["capabilities"]["network"], "findings": [item["category"] for item in plan["findings"]], "files": sorted(item.name for item in (package / "input").iterdir()), "sandbox": "<Networking>Disable</Networking>" in (package / "AegisTestLab.wsb").read_text()} == {"risk": "critical", "network": False, "findings": ["destructive-filesystem", "network"], "files": ["Run-AegisTestLab.ps1", "danger.ps1", "manifest.json", "synthetic-data.json", "test-plan.json"], "sandbox": True}


class TestSandboxResourceLimits:
    def test_sandbox_config_includes_memory_limit(self, tmp_path):
        plan = create_test_plan({"test.ps1": "Write-Host 'test'"})
        package = create_test_package(tmp_path, {"test.ps1": "Write-Host 'test'"}, plan)
        wsb_content = (package / "AegisTestLab.wsb").read_text()
        assert "<MemoryInMB>4096</MemoryInMB>" in wsb_content

    def test_sandbox_config_includes_cpu_limit(self, tmp_path):
        plan = create_test_plan({"test.ps1": "Write-Host 'test'"})
        package = create_test_package(tmp_path, {"test.ps1": "Write-Host 'test'"}, plan)
        wsb_content = (package / "AegisTestLab.wsb").read_text()
        assert "<CPULimit>100</CPULimit>" in wsb_content

    def test_sandbox_config_disables_networking(self, tmp_path):
        plan = create_test_plan({"test.ps1": "Write-Host 'test'"})
        package = create_test_package(tmp_path, {"test.ps1": "Write-Host 'test'"}, plan)
        wsb_content = (package / "AegisTestLab.wsb").read_text()
        assert "<Networking>Disable</Networking>" in wsb_content
        assert "<ClipboardRedirection>Disable</ClipboardRedirection>" in wsb_content
        assert "<ProtectedClient>Enable</ProtectedClient>" in wsb_content

    def test_custom_resource_limits_applied(self, tmp_path):
        plan = create_test_plan({"test.ps1": "Write-Host 'test'"})
        plan["resourceLimits"] = {"memoryMB": 2048, "cpuPercent": 50}
        package = create_test_package(tmp_path, {"test.ps1": "Write-Host 'test'"}, plan)
        wsb_content = (package / "AegisTestLab.wsb").read_text()
        assert "<MemoryInMB>2048</MemoryInMB>" in wsb_content
        assert "<CPULimit>50</CPULimit>" in wsb_content


class TestSandboxLaunch:
    def test_launch_sandbox_returns_error_when_file_missing(self, tmp_path):
        missing_file = tmp_path / "nonexistent.wsb"
        result = launch_sandbox(missing_file)
        assert result["status"] == "error"
        assert "not found" in result["message"].lower()

    def test_launch_sandbox_returns_metadata_when_launched(self, tmp_path):
        # Create a minimal valid .wsb file
        wsb_file = tmp_path / "test.wsb"
        wsb_file.write_text("<Application><Name>Test</Name><Executable>notepad.exe</Executable></Application>")
        result = launch_sandbox(wsb_file)
        assert result["status"] in ["launched", "error"]  # May fail if Windows Sandbox not installed
        if result["status"] == "launched":
            assert "process_id" in result
            assert "sandbox_file" in result
            assert "timeout_seconds" in result


class TestSandboxCleanup:
    def test_cleanup_removes_output_directory(self, tmp_path):
        package_root = tmp_path / "package"
        package_root.mkdir()
        output_dir = package_root / "output"
        output_dir.mkdir()
        (output_dir / "evidence.json").write_text('{"test": "data"}')
        
        result = cleanup_sandbox(package_root)
        
        assert result["status"] == "success"
        assert not output_dir.exists()
        assert any("output" in str(action).lower() for action in result.get("actions", []))

    def test_cleanup_handles_missing_output_directory(self, tmp_path):
        package_root = tmp_path / "package"
        package_root.mkdir()
        
        result = cleanup_sandbox(package_root)
        
        assert result["status"] == "success"

    def test_cleanup_returns_actions_and_errors(self, tmp_path):
        package_root = tmp_path / "package"
        package_root.mkdir()
        output_dir = package_root / "output"
        output_dir.mkdir()
        
        result = cleanup_sandbox(package_root)
        
        assert "actions" in result
        assert "errors" in result


class TestSandboxIsolation:
    def test_plan_detects_network_capabilities(self, tmp_path):
        plan = create_test_plan({"network.ps1": "Invoke-WebRequest http://example.com"})
        assert plan["capabilities"]["network"] is False
        assert any(f["category"] == "network" for f in plan["findings"])

    def test_plan_detects_destructive_capabilities(self, tmp_path):
        plan = create_test_plan({"destructive.ps1": "Remove-Item C:\\ -Recurse"})
        assert plan["risk"] == "critical"
        assert any(f["category"] == "destructive-filesystem" for f in plan["findings"])

    def test_plan_sets_fail_closed_defaults(self, tmp_path):
        plan = create_test_plan({"safe.ps1": "Write-Host 'hello'"})
        assert plan["capabilities"]["network"] is False
        assert plan["capabilities"]["credentials"] is False
        assert plan["capabilities"]["hostWrite"] is False

