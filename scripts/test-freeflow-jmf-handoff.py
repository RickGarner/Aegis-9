#!/usr/bin/env python3
"""Test FreeFlow JMF endpoint with the exact working format from handoff document."""

import httpx
import xml.etree.ElementTree as ET

# FreeFlow server from config
FREEFLOW_SERVER = "10.30.67.21"
FREEFLOW_PORT = 7751
JMF_URL = f"http://{FREEFLOW_SERVER}:{FREEFLOW_PORT}/FreeFlowCore/"

# Exact working format from handoff document
JMF_WORKING_FORMAT = b'''<?xml version="1.0" encoding="UTF-8"?>
<JMF xmlns="http://www.CIP4.org/JDFSchema_1_1"
     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
     MaxVersion="1.6"
     SenderID="AEGIS9"
     TimeStamp="2026-09-23T12:00:00Z"
     Version="1.6">
    <Query ID="q-test-001"
           Type="KnownDevices"
           xsi:type="QueryKnownDevices">
        <DeviceFilter DeviceDetails="Brief"/>
    </Query>
</JMF>
'''

def test_jmf_endpoint(url, xml_data, format_name):
    """Test JMF query against FreeFlow endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {format_name}")
    print(f"URL: {url}")
    print(f"{'='*60}")
    
    try:
        response = httpx.post(
            url,
            content=xml_data,
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
            jdf_ns = 'http://www.CIP4.org/JDFSchema_1_1'
            device_count = len(root.findall(f'.//{{{jdf_ns}}}DeviceInfo'))
            print(f"Device count: {device_count}")
            
            # Print response preview
            print(f"\nResponse preview (first 1500 chars):")
            print(response.text[:1500])
            
        except ET.ParseError as e:
            print(f"✗ XML parsing: FAILED - {e}")
            print(f"\nRaw response (first 1500 chars):")
            print(response.text[:1500])
            
    except httpx.HTTPError as e:
        print(f"✗ HTTP Error: {type(e).__name__}: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response status: {e.response.status_code}")
            print(f"Response body (first 500 chars):")
            print(e.response.text[:500])
    except Exception as e:
        print(f"✗ Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print(f"FreeFlow JMF Test - Working Format from Handoff")
    print(f"Target: {JMF_URL}")
    
    test_jmf_endpoint(JMF_URL, JMF_WORKING_FORMAT, "Working Format (from handoff document)")
    
    print(f"\n{'='*60}")
    print("Test complete")
    print(f"{'='*60}")
