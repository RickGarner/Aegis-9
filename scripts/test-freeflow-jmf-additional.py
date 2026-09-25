#!/usr/bin/env python3
"""Test additional FreeFlow JMF query formats."""

import urllib.request
import urllib.error

FREEFLOW_PRIMARY = "10.30.67.21"
FREEFLOW_PORT = 7751
JMF_URL = f"http://{FREEFLOW_PRIMARY}:{FREEFLOW_PORT}/FreeFlowCore/"

# Minimal JMF query
JMF_MINIMAL = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <Brief/>
  </query>
</jmf>
"""

# JMF with DeviceList (not DeviceFilter)
JMF_DEVICE_LIST = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <DeviceList/>
  </query>
</jmf>
"""

# JMF with status filter
JMF_STATUS = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <Brief>
      <DeviceFilter status="*"/>
    </Brief>
  </query>
</jmf>
"""

# Xerox-specific JMF format
XEROX_JMF = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query xsi:type="QueryKnownDevices" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <Brief>
      <DeviceFilter/>
    </Brief>
  </query>
</jmf>
"""

# Empty query (just to test endpoint)
EMPTY_QUERY = """<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
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
            print(f"\nResponse preview:")
            print(response_text[:1000])
            return True
            
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} {e.reason}")
        try:
            error_body = e.read().decode('utf-8')
            # Look for useful error info
            if "NullPointerException" in error_body:
                print("Server-side NullPointerException detected")
            if "400" in str(e.code):
                print("Bad request - client-side error")
        except:
            pass
        return False
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        return False
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print(f"FreeFlow JMF Test - Additional Formats")
    print(f"Target: {JMF_URL}")
    
    formats = [
        ("Minimal JMF", JMF_MINIMAL),
        ("DeviceList", JMF_DEVICE_LIST),
        ("Status Filter", JMF_STATUS),
        ("Xerox-specific", XEROX_JMF),
        ("Empty query", EMPTY_QUERY),
    ]
    
    results = {}
    for name, xml in formats:
        results[name] = test_jmf_format(name, xml)
    
    print(f"\n{'='*60}")
    print("Summary:")
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")
    print(f"{'='*60}")
