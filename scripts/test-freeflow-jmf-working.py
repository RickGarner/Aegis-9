#!/usr/bin/env python3
"""Test FreeFlow JMF endpoint with the working query format from handoff notes."""

import httpx
import xml.etree.ElementTree as ET

# FreeFlow server from config
FREEFLOW_SERVER = "10.30.67.21"
FREEFLOW_PORT = 7751
JMF_URL = f"http://{FREEFLOW_SERVER}:{FREEFLOW_PORT}/FreeFlowCore/"

# Working format from handoff notes (produces HTTP 200)
# Brief DeviceFilter + CIP4 typed query
JMF_WORKING_FORMAT = """<?xml version="1.0" encoding="UTF-8"?>
<printSystem xmlns="http://www.CIP4.org/JDFSchema_1_1" xsi:type="QueryKnownDevices" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <query>
    <maxVersion>1.2</maxVersion>
  </query>
</printSystem>
"""

def test_jmf_endpoint(url, xml_data, format_name):
    """Test JMF query against FreeFlow endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {format_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        response = httpx.post(
            url,
            content=xml_data.encode('utf-8'),
            headers={
                'Content-Type': 'application/vnd.cip4-jmf+xml',
                'Accept': 'application/vnd.cip4-jmf+xml, application/xml, text/xml'
            },
            timeout=30
        )
        
        print(f"Status: {response.status_code} {response.reason_phrase}")
        print(f"Response length: {len(response.content)} bytes")
        
        # Try to parse as XML
        try:
            root = ET.fromstring(response.content)
            print("✓ XML parsing: SUCCESS")
            print(f"Root tag: {root.tag}")
            
            # Count device info elements
            device_count = len(root.findall('.//{*}DeviceInfo', namespaces={'': 'http://www.CIP4.org/JDFSchema_1_1'}))
            print(f"Device count: {device_count}")
            
            # Print response preview
            print(f"\nResponse preview (first 1000 chars):")
            print(response.text[:1000])
            
        except ET.ParseError as e:
            print(f"✗ XML parsing: FAILED - {e}")
            print(f"\nRaw response (first 1000 chars):")
            print(response.text[:1000])
            
    except httpx.HTTPError as e:
        print(f"✗ HTTP Error: {type(e).__name__}: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body (first 500 chars):")
            print(e.response.text[:500])
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print(f"FreeFlow JMF Test - Working Format")
    print(f"Target: {JMF_URL}")
    
    test_jmf_endpoint(JMF_URL, JMF_WORKING_FORMAT, "Working Format (Brief DeviceFilter + CIP4 typed)")
    
    print(f"\n{'='*60}")
    print("Test complete")
    print(f"{'='*60}")
