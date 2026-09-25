#!/usr/bin/env python3
"""Test FreeFlow JMF endpoint with different query formats."""

import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

FREEFLOW_PRIMARY = "10.30.67.21"
FREEFLOW_PORT = 7751
JMF_URL = f"http://{FREEFLOW_PRIMARY}:{FREEFLOW_PORT}/FreeFlowCore/"

# Format from handoff notes that produced HTTP 200
JMF_QUERY_FORMAT_1 = """<?xml version="1.0" encoding="UTF-8"?>
<printSystem xmlns="http://www.CIP4.org/JDFSchema_1_1">
  <query xsi:type="QueryKnownDevices" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <maxVersion>1.2</maxVersion>
  </query>
</printSystem>
"""

# Simpler format with Brief DeviceFilter
JMF_QUERY_FORMAT_2 = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <Brief>
      <DeviceFilter/>
    </Brief>
  </query>
</jmf>
"""

# CIP4 typed query with Brief DeviceFilter
JMF_QUERY_FORMAT_3 = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <Brief>
      <DeviceFilter/>
    </Brief>
  </query>
</jmf>
"""

def test_jmf_format(format_name, xml_data):
    """Test a JMF query format against the FreeFlow endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing: {format_name}")
    print(f"{'='*60}")
    
    try:
        req = urllib.request.Request(
            JMF_URL,
            data=xml_data.encode('utf-8'),
            method='POST'
        )
        req.add_header('Content-Type', 'application/vnd.cip4-jmf+xml')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            print(f"Status: {response.status} {response.reason}")
            response_text = response.read().decode('utf-8')
            print(f"Response length: {len(response_text)} bytes")
            
            # Try to parse as XML
            try:
                root = ET.fromstring(response_text)
                print("XML parsing: SUCCESS")
                print(f"Root tag: {root.tag}")
                
                # Print first 500 chars of response
                print(f"\nResponse preview (first 500 chars):")
                print(response_text[:500])
                
            except ET.ParseError as e:
                print(f"XML parsing: FAILED - {e}")
                print(f"\nRaw response (first 500 chars):")
                print(response_text[:500])
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        print(f"Response headers: {dict(e.headers)}")
        try:
            error_body = e.read().decode('utf-8')
            print(f"Error body (first 500 chars):")
            print(error_body[:500])
        except:
            pass
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    print(f"FreeFlow JMF Test")
    print(f"Target: {JMF_URL}")
    
    test_jmf_format("CIP4 QueryKnownDevices", JMF_QUERY_FORMAT_1)
    test_jmf_format("JMF with Brief DeviceFilter (format 2)", JMF_QUERY_FORMAT_2)
    test_jmf_format("JMF with Brief DeviceFilter (format 3)", JMF_QUERY_FORMAT_3)
    
    print(f"\n{'='*60}")
    print("Test complete")
    print(f"{'='*60}")
