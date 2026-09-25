#!/usr/bin/env python3
"""
Onsite validation script for MOVEit HA and FreeFlow Core servers.
Uses urllib instead of httpx for better compatibility.
"""

import asyncio
import json
import socket
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET


# Configuration - can be overridden with IP addresses if DNS fails
MOVEIT_PRIMARY = "BSOAUTALB001"
MOVEIT_SECONDARY = "BSOAUTALB002"
MOVEIT_WEB_ADMIN_PORT = 443
MOVEIT_WEB_ADMIN_PATH = "/WebAdmin"

FREEFLOW_PRIMARY = "BSOXERALB001"
FREEFLOW_SECONDARY = "BSOXERALB002"
FREEFLOW_JMF_PORT = 7751


def resolve_hostname(hostname: str) -> str:
    """Resolve hostname to IP address."""
    try:
        ip = socket.gethostbyname(hostname)
        return ip
    except socket.gaierror:
        print(f"  Warning: Could not resolve {hostname}, using hostname directly")
        return hostname


async def check_host_reachable(hostname: str, timeout: float = 5.0) -> bool:
    """Check if a host is reachable via DNS resolution."""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"    Resolved {hostname} to {ip}")
        return True
    except socket.gaierror as e:
        print(f"    DNS resolution failed for {hostname}: {e}")
        return False
    except Exception as e:
        print(f"    Host check failed for {hostname}: {e}")
        return False


def check_tcp_port(hostname: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a TCP port is open on a host."""
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(
            asyncio.wait_for(
                asyncio.get_event_loop().sock_connect(
                    socket.socket(socket.AF_INET, socket.SOCK_STREAM),
                    (hostname, port)
                ),
                timeout=timeout
            )
        )
    except Exception:
        return False


def check_moveit_web_admin(hostname: str) -> dict[str, Any]:
    """Check MOVEit Web Admin endpoint using urllib."""
    result = {
        "hostname": hostname,
        "web_admin_reachable": False,
        "http_status": None,
        "response_ms": None,
        "detail": ""
    }
    
    # Try different common MOVEit Web Admin paths
    paths_to_try = [
        "/WebAdmin/",
        "/webadmin/",
        "/",
        "/MoveIt/WebAdmin/",
    ]
    
    for path in paths_to_try:
        url = f"https://{hostname}:{MOVEIT_WEB_ADMIN_PORT}{path}"
        try:
            import time
            start = time.perf_counter()
            
            # Create request with SSL context that doesn't verify certs
            ctx = urllib.request.ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = urllib.request.ssl.CERT_NONE
            
            req = urllib.request.Request(url, method='GET')
            with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
                elapsed = (time.perf_counter() - start) * 1000
                result["http_status"] = response.status
                result["response_ms"] = round(elapsed)
                result["web_admin_reachable"] = True
                result["detail"] = f"Web Admin at {path} returned HTTP {response.status}"
                if response.status == 200:
                    result["detail"] += " - Login page detected"
                elif response.status == 401:
                    result["detail"] += " - Authentication required (protected endpoint)"
                break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue  # Try next path
            result["http_status"] = e.code
            result["detail"] = f"Web Admin at {path} returned HTTP {e.code}"
            if e.code == 401:
                result["detail"] += " - Authentication required (protected endpoint)"
            break
        except urllib.error.URLError as e:
            result["detail"] = f"HTTPS URL error at {path}: {e.reason}"
        except Exception as e:
            result["detail"] = f"Web Admin check failed: {type(e).__name__}: {str(e)}"
    
    return result


def check_freeflow_jmf(hostname: str, jmf_url: str) -> dict[str, Any]:
    """Check FreeFlow JMF KnownDevices endpoint using urllib."""
    result = {
        "hostname": hostname,
        "jmf_reachable": False,
        "http_status": None,
        "response_ms": None,
        "device_count": 0,
        "detail": ""
    }
    
    # JMF request XML
    jmf_request = """<?xml version="1.0" encoding="UTF-8"?>
<printSystem xmlns="http://www.CIP4.org/JDFSchema_1_1" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://www.CIP4.org/JDFSchema_1_1 http://www.CIP4.org/JDFSchema_1_1/JDF.xsd">
  <query xsi:type="QueryKnownDevices">
    <maxVersion>1.2</maxVersion>
    <deviceFilter brief="true"/>
  </query>
</printSystem>"""
    
    try:
        import time
        start = time.perf_counter()
        
        req = urllib.request.Request(
            jmf_url,
            data=jmf_request.encode('utf-8'),
            headers={
                "Content-Type": "application/vnd.cip4-jmf+xml",
                "Accept": "application/vnd.cip4-jmf+xml, application/xml, text/xml"
            },
            method='POST'
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            elapsed = (time.perf_counter() - start) * 1000
            result["http_status"] = response.status
            result["response_ms"] = round(elapsed)
            
            if response.status == 200:
                result["jmf_reachable"] = True
                # Parse device count from XML response
                try:
                    root = ET.fromstring(response.read())
                    devices = root.findall(".//{*}device", {"": "http://www.CIP4.org/JDFSchema_1_1"})
                    result["device_count"] = len(devices)
                    result["detail"] = f"KnownDevices returned {len(devices)} device(s)"
                except ET.ParseError:
                    result["detail"] = f"KnownDevices returned HTTP 200 but XML parse failed"
            else:
                result["detail"] = f"JMF endpoint returned HTTP {response.status}"
    except urllib.error.HTTPError as e:
        result["http_status"] = e.code
        result["detail"] = f"JMF endpoint returned HTTP {e.code}"
        if e.code == 401:
            result["detail"] += " - Authentication required"
    except urllib.error.URLError as e:
        result["detail"] = f"JMF URL error: {e.reason}"
    except Exception as e:
        result["detail"] = f"JMF check failed: {type(e).__name__}: {str(e)}"
    
    return result


def check_windows_service(hostname: str, service_name: str) -> dict[str, Any]:
    """Check Windows service status via PowerShell."""
    result = {
        "hostname": hostname,
        "service_name": service_name,
        "service_running": False,
        "detail": ""
    }
    
    try:
        cmd = f'powershell -Command "Get-Service -Name \'{service_name}\' -ComputerName \'{hostname}\' | Select-Object Name, Status | ConvertTo-Json"'
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10, shell=True)
        
        if proc.returncode == 0:
            import json
            service_data = json.loads(proc.stdout)
            result["service_running"] = service_data.get("Status") == "Running"
            result["detail"] = f"Service status: {service_data.get('Status')}"
        else:
            result["detail"] = f"PowerShell command failed: {proc.stderr[:200]}"
    except Exception as e:
        result["detail"] = f"Service check failed: {type(e).__name__}: {str(e)}"
    
    return result


def run_full_discovery():
    """Run complete onsite discovery."""
    print(f"\n{'='*60}")
    print(f"ON-SITE DISCOVERY - {datetime.now(timezone.utc).isoformat()}")
    print(f"{'='*60}\n")
    
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "moveit": {},
        "freeflow": {},
        "services": {}
    }
    
    # Check host reachability
    print("Checking host reachability...")
    hosts_to_check = [MOVEIT_PRIMARY, MOVEIT_SECONDARY, FREEFLOW_PRIMARY, FREEFLOW_SECONDARY]
    for host in hosts_to_check:
        reachable = asyncio.run(check_host_reachable(host))
        print(f"  {host}: {'REACHABLE' if reachable else 'UNREACHABLE'}")
        results["hosts"] = {host: reachable}
    
    # Check MOVEit Web Admin
    print(f"\nChecking MOVEit Web Admin endpoints...")
    for hostname in [MOVEIT_PRIMARY, MOVEIT_SECONDARY]:
        result = check_moveit_web_admin(hostname)
        results["moveit"][hostname] = result
        status = "OK" if result["web_admin_reachable"] else "FAILED"
        print(f"  {hostname}: {status} - {result['detail']}")
    
    # Check FreeFlow JMF
    print(f"\nChecking FreeFlow JMF endpoints...")
    jmf_configs = [
        (FREEFLOW_PRIMARY, f"http://{resolve_hostname(FREEFLOW_PRIMARY)}:7751/FreeFlowCore"),
        (FREEFLOW_SECONDARY, f"http://{resolve_hostname(FREEFLOW_SECONDARY)}:7751/FreeFlowCore")
    ]
    for hostname, jmf_url in jmf_configs:
        result = check_freeflow_jmf(hostname, jmf_url)
        results["freeflow"][hostname] = result
        status = "OK" if result["jmf_reachable"] else "FAILED"
        print(f"  {hostname}: {status} - {result['detail']}")
    
    # Check Windows services
    print(f"\nChecking Windows services...")
    # Try common MOVEit service name patterns
    service_patterns = ["MoveIt", "MoveIt*", "Progress*", "Progress_MoveIt*"]
    checked_services = set()
    
    for hostname in [MOVEIT_PRIMARY, MOVEIT_SECONDARY]:
        resolved_host = resolve_hostname(hostname)
        # Try to enumerate services with MoveIt in the name
        try:
            cmd = f'powershell -Command "Get-Service -ComputerName \'{resolved_host}\' | Where-Object {{ $_.DisplayName -like \'*MoveIt*\' }} | Select-Object Name, DisplayName, Status | ConvertTo-Json"'
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15, shell=True)
            
            if proc.returncode == 0 and proc.stdout.strip():
                import json
                services = json.loads(proc.stdout)
                if isinstance(services, list):
                    for svc in services:
                        svc_name = svc.get("Name", "")
                        svc_display = svc.get("DisplayName", "")
                        svc_status = svc.get("Status", "")
                        results["services"][f"{hostname}/{svc_name}"] = {
                            "hostname": hostname,
                            "service_name": svc_name,
                            "display_name": svc_display,
                            "service_running": svc_status == "Running",
                            "detail": f"Status: {svc_status}"
                        }
                        print(f"  {hostname}/{svc_name}: {svc_status} - {svc_display}")
                        checked_services.add(svc_name)
        except Exception as e:
            print(f"  Service enumeration failed for {hostname}: {e}")
    
    # Save results
    output_file = Path("storage/onsite-discovery-2026-09-21.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Discovery results saved to: {output_file}")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    run_full_discovery()
