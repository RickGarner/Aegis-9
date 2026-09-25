#!/usr/bin/env python3
"""Test FreeFlow job control operations against BSOXERALB002."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.config import Settings
from app.freeflow_jmf import FreeFlowJmfService, build_queue_status_request
import httpx
import xml.etree.ElementTree as ET


def test_job_control_operations():
    """Test job control operations against BSOXERALB002."""
    settings = Settings()
    service = FreeFlowJmfService(settings)
    
    # Target BSOXERALB002
    server_name = "BSOXERALB002"
    server_url = "http://BSOXERALB002:7751/FreeFlowCore"
    
    print("=" * 80)
    print(f"Testing Job Control Operations on {server_name}")
    print(f"URL: {server_url}")
    print("=" * 80)
    
    # Test 1: QueueStatus - Get recent jobs
    print("\n1. QueueStatus - Get Recent Jobs")
    print("-" * 40)
    try:
        response = httpx.post(
            server_url,
            content=build_queue_status_request(),
            headers={"Content-Type": "application/vnd.cip4-jmf+xml"},
            timeout=30,
        )
        print(f"HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            # Parse response
            root = ET.fromstring(response.content)
            print(f"\nResponse Root: {root.tag.rsplit('}', 1)[-1]}")
            print(f"ReturnCode: {root.attrib.get('ReturnCode', 'N/A')}")
            
            # Count QueueEntry elements
            queue_entries = list(root.iter())
            entry_count = sum(1 for elem in queue_entries if elem.tag.rsplit("}", 1)[-1] == "QueueEntry")
            print(f"Queue Entries Found: {entry_count}")
            
            # Show first few entries
            if entry_count > 0:
                print(f"\nFirst 3 Queue Entries:")
                entry_num = 0
                for elem in root.iter():
                    if elem.tag.rsplit("}", 1)[-1] == "QueueEntry":
                        if entry_num >= 3:
                            break
                        entry_num += 1
                        print(f"\n  Entry #{entry_num}:")
                        for attr, value in elem.attrib.items():
                            attr_name = attr.rsplit("}", 1)[-1]
                            if attr_name in ["QueueEntryID", "JobID", "JobName", "Status"]:
                                print(f"    {attr_name}: {value}")
        else:
            print(f"Error Response:\n{response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Try Status query on a specific device
    print("\n2. Status Query - Check Device Status")
    print("-" * 40)
    
    # First, get known devices to find a device ID
    devices_response = httpx.post(
        server_url,
        content=b'''<?xml version="1.0" encoding="utf-8"?>
<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     MaxVersion="1.6"
     SenderID="AEGIS9"
     TimeStamp="2026-09-23T18:00:00Z"
     Version="1.6">
    <Query ID="q-devices" Type="KnownDevices" xsi:type="QueryKnownDevices">
        <DeviceFilter DeviceDetails="Brief"/>
    </Query>
</JMF>''',
        headers={"Content-Type": "application/vnd.cip4-jmf+xml"},
        timeout=30,
    )
    
    if devices_response.status_code == 200:
        root = ET.fromstring(devices_response.content)
        devices = list(root.iter())
        device_count = sum(1 for elem in devices if elem.tag.rsplit("}", 1)[-1] == "DeviceInfo")
        print(f"Devices Found: {device_count}")
        
        # Try to get status for first device
        if device_count > 0:
            print("\nAttempting Status query on first device...")
            # Note: Actual Status query would require a specific DeviceID
            print("Status query requires specific DeviceID from KnownDevices response")
    else:
        print(f"Failed to get devices: {devices_response.status_code}")
    
    # Test 3: Test KnownControllers
    print("\n3. KnownControllers - Discover Controllers")
    print("-" * 40)
    
    controllers_request = b'''<?xml version="1.0" encoding="utf-8"?>
<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     MaxVersion="1.6"
     SenderID="AEGIS9"
     TimeStamp="2026-09-23T18:00:00Z"
     Version="1.6">
    <Query ID="q-controllers" Type="KnownControllers" xsi:type="QueryKnownControllers">
        <DeviceFilter DeviceDetails="Brief"/>
    </Query>
</JMF>'''
    
    try:
        response = httpx.post(
            server_url,
            content=controllers_request,
            headers={"Content-Type": "application/vnd.cip4-jmf+xml"},
            timeout=30,
        )
        print(f"HTTP Status: {response.status_code}")
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            controllers = list(root.iter())
            controller_count = sum(1 for elem in controllers if elem.tag.rsplit("}", 1)[-1] == "ControllerInfo")
            print(f"Controllers Found: {controller_count}")
        else:
            print(f"Error:\n{response.text[:500]}")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n" + "=" * 80)
    print("Job Control Testing Complete")
    print("=" * 80)


if __name__ == "__main__":
    test_job_control_operations()
