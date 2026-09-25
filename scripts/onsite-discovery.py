#!/usr/bin/env python3
"""
Onsite validation script for MOVEit HA and FreeFlow Core servers.
Run this from a machine with physical network access to the BSOC internal network.
"""

import asyncio
import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


# Configuration - update these with actual internal network values
MOVEIT_PRIMARY = "BSOAUTALB001"
MOVEIT_SECONDARY = "BSOAUTALB002"
MOVEIT_WEB_ADMIN_PORT = 443  # HTTPS
MOVEIT_WEB_ADMIN_PATH = "/WebAdmin"

FREEFLOW_PRIMARY = "BSOXERALB001"
FREEFLOW_SECONDARY = "BSOXERALB002"
FREEFLOW_JMF_PORT = 7751


async def check_host_reachable(hostname: str, timeout: float = 5.0) -> bool:
    """Check if a host is reachable via DNS resolution."""
    try:
        await asyncio.get_event_loop().getaddrinfo(hostname, None, timeout=timeout)
        return True
    except Exception:
        return False


async def check_tcp_port(hostname: str, port: int, timeout: float = 3.0) -> bool:
    """Check if a TCP port is open on a host."""
    try:
        loop = asyncio.get_event_loop()
        await loop.sock_connect(socket.socket(socket.AF_INET, socket.SOCK_STREAM), (hostname, port))
        return True
    except Exception:
        return False


async def check_moveit_web_admin(hostname: str) -> dict[str, Any]:
    """Check MOVEit Web Admin endpoint."""
    result = {
        "hostname": hostname,
        "web_admin_reachable": False,
        "http_status": None,
        "response_ms": None,
        "detail": ""
    }
    
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=10.0)) as client:
            start = asyncio.get_event_loop().time()
            # Try HTTPS first (typical for MOVEit)
            try:
                response = await client.get(f"https://{hostname}:{MOVEIT_WEB_ADMIN_PORT}{MOVEIT_WEB_ADMIN_PATH}/", 
                                           allow_redirects=True)
                elapsed = (asyncio.get_event_loop().time() - start) * 1000
                result["http_status"] = response.status_code
                result["response_ms"] = round(elapsed)
                result["web_admin_reachable"] = True
                result["detail"] = f"Web Admin returned HTTP {response.status_code}"
                if response.status_code == 200:
                    result["detail"] += " - Login page detected"
                elif response.status_code == 401:
                    result["detail"] += " - Authentication required (protected endpoint)"
            except httpx.HTTPError as e:
                result["detail"] = f"HTTPS error: {type(e).__name__}"
    except Exception as e:
        result["detail"] = f"Web Admin check failed: {type(e).__name__}: {str(e)}"
    
    return result


async def check_freeflow_jmf(hostname: str, jmf_url: str) -> dict[str, Any]:
    """Check FreeFlow JMF KnownDevices endpoint."""
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
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout=30.0)) as client:
            start = asyncio.get_event_loop().time()
            response = await client.post(
                jmf_url,
                content=jmf_request.encode('utf-8'),
                headers={
                    "Content-Type": "application/vnd.cip4-jmf+xml",
                    "Accept": "application/vnd.cip4-jmf+xml, application/xml, text/xml"
                }
            )
            elapsed = (asyncio.get_event_loop().time() - start) * 1000
            result["http_status"] = response.status_code
            result["response_ms"] = round(elapsed)
            
            if response.status_code == 200:
                result["jmf_reachable"] = True
                # Parse device count from XML response
                import xml.etree.ElementTree as ET
                try:
                    root = ET.fromstring(response.content)
                    devices = root.findall(".//{*}device", {"": "http://www.CIP4.org/JDFSchema_1_1"})
                    result["device_count"] = len(devices)
                    result["detail"] = f"KnownDevices returned {len(devices)} device(s)"
                except ET.ParseError:
                    result["detail"] = f"KnownDevices returned HTTP 200 but XML parse failed"
            elif response.status_code == 401:
                result["detail"] = "JMF endpoint returned HTTP 401 (authentication required)"
            else:
                result["detail"] = f"JMF endpoint returned HTTP {response.status_code}"
    except httpx.TimeoutException:
        result["detail"] = "JMF request timed out (30s)"
    except httpx.HTTPError as e:
        result["detail"] = f"JMF HTTP error: {type(e).__name__}: {str(e)}"
    except Exception as e:
        result["detail"] = f"JMF check failed: {type(e).__name__}: {str(e)}"
    
    return result


def check_windows_service(hostname: str, service_name: str) -> dict[str, Any]:
    """Check Windows service status via WMI."""
    result = {
        "hostname": hostname,
        "service_name": service_name,
        "service_running": False,
        "detail": ""
    }
    
    try:
        # Use PowerShell to check service status
        cmd = f'powershell -Command "Get-Service -Name \'{service_name}\' -ComputerName \'{hostname}\' | Select-Object Name, Status, StartType | ConvertTo-Json"'
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if proc.returncode == 0:
            import json
            service_data = json.loads(proc.stdout)
            result["service_running"] = service_data.get("Status") == "Running"
            result["detail"] = f"Service status: {service_data.get('Status')}, StartType: {service_data.get('StartType')}"
        else:
            result["detail"] = f"PowerShell command failed: {proc.stderr}"
    except Exception as e:
        result["detail"] = f"Service check failed: {type(e).__name__}: {str(e)}"
    
    return result


async def run_full_discovery():
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
    for host in [MOVEIT_PRIMARY, MOVEIT_SECONDARY, FREEFLOW_PRIMARY, FREEFLOW_SECONDARY]:
        reachable = await check_host_reachable(host)
        print(f"  {host}: {'REACHABLE' if reachable else 'UNREACHABLE'}")
        results["hosts"] = {host: reachable}
    
    # Check MOVEit Web Admin
    print(f"\nChecking MOVEit Web Admin endpoints...")
    for hostname in [MOVEIT_PRIMARY, MOVEIT_SECONDARY]:
        result = await check_moveit_web_admin(hostname)
        results["moveit"][hostname] = result
        status = "OK" if result["web_admin_reachable"] else "FAILED"
        print(f"  {hostname}: {status} - {result['detail']}")
    
    # Check FreeFlow JMF
    print(f"\nChecking FreeFlow JMF endpoints...")
    jmf_configs = [
        (FREEFLOW_PRIMARY, "http://BSOXERALB001:7751/FreeFlowCore"),
        (FREEFLOW_SECONDARY, "http://BSOXERALB002:7751/FreeFlowCore")
    ]
    for hostname, jmf_url in jmf_configs:
        result = await check_freeflow_jmf(hostname, jmf_url)
        results["freeflow"][hostname] = result
        status = "OK" if result["jmf_reachable"] else "FAILED"
        print(f"  {hostname}: {status} - {result['detail']}")
    
    # Check Windows services
    print(f"\nChecking Windows services...")
    moveit_services = ["MoveIt", "MoveItAdmin", "MoveItScheduler"]
    for service in moveit_services:
        for hostname in [MOVEIT_PRIMARY, MOVEIT_SECONDARY]:
            result = check_windows_service(hostname, service)
            results["services"][f"{hostname}/{service}"] = result
            status = "RUNNING" if result["service_running"] else "STOPPED"
            print(f"  {hostname}/{service}: {status} - {result['detail']}")
    
    # Save results
    output_file = Path("storage/onsite-discovery-2026-09-21.json")
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(json.dumps(results, indent=2, default=str), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"Discovery results saved to: {output_file}")
    print(f"{'='*60}\n")
    
    return results


if __name__ == "__main__":
    asyncio.run(run_full_discovery())
