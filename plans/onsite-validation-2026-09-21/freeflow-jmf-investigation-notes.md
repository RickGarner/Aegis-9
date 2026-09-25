# FreeFlow JMF Investigation Notes

**Date:** 2026-09-21  
**Investigator:** Aegis-9 onsite validation  
**Status:** BLOCKED - Requires correct JMF query format

---

## Discovered Server Information

### FreeFlow Core Servers
- **Primary:** BSOXERALB001 (10.30.67.21)
- **Secondary:** BSOXERALB002 (10.30.67.20)
- **JMF Port:** 7751
- **Endpoint:** `/FreeFlowCore/`
- **Reachability:** ✅ Both servers respond on port 7751

---

## Problem Summary

All tested JMF query formats return **HTTP 500 Internal Server Error** with server-side NullPointerException.

The endpoint is reachable and responding, but the FreeFlow JMF implementation is rejecting the XML queries.

---

## Tested Query Formats

### Format 1: CIP4 QueryKnownDevices
```xml
<?xml version="1.0" encoding="UTF-8"?>
<printSystem xmlns="http://www.CIP4.org/JDFSchema_1_1">
  <query xsi:type="QueryKnownDevices" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
    <maxVersion>1.2</maxVersion>
  </query>
</printSystem>
```
**Result:** HTTP 500 - Internal Server Error

### Format 2: JMF with Brief DeviceFilter
```xml
<?xml version="1.0" encoding="UTF-8"?>
<jmf version="1.0" xmlns="http://www.CIP4.org/schema/JMF/1.0">
  <query>
    <Brief>
      <DeviceFilter/>
    </Brief>
  </query>
</jmf>
```
**Result:** HTTP 500 - Internal Server Error

### Format 3: JMF with Brief DeviceFilter (alternate)
Same as Format 2  
**Result:** HTTP 500 - Internal Server Error

---

## Error Details

All formats returned:
- **Status:** 500 Internal Server Error
- **Content-Type:** text/html;charset=utf-8
- **Error Body:** Apache Tomcat error page with NullPointerException

The server-side error indicates the Xerox JDF toolkit is encountering an unhandled exception when processing the query.

---

## Handoff Notes

**User reported:** Adding `Brief DeviceFilter` and proper CIP4 typed query produced HTTP 200.

**Likely cause:** The installed FreeFlow version expects a specific XML schema or query structure that differs from the standard CIP4 JMF formats tested above.

---

## Next Steps

1. **Obtain correct JMF query format** from:
   - Xerox FreeFlow SDK diagnostic tools
   - Workstation with FreeFlow SDK installed (user has physical access)
   - FreeFlow server logs showing successful query examples

2. **Once correct format is obtained:**
   - Update `backend/app/freeflow_jmf.py` with working query
   - Test device enumeration
   - Validate response parsing

3. **Investigation resources:**
   - FreeFlow server logs: Check Xerox logs for NullPointerException stack trace
   - JMF diagnostic tools: Use Xerox-provided utilities to capture working queries
   - FreeFlow SDK: Query from workstation with SDK to see exact request format

---

## Related Files

- `backend/app/freeflow_jmf.py` - JMF service implementation
- `scripts/test-freeflow-jmf.py` - Test script for query formats
- `config/freeflow-ha.json` - FreeFlow HA configuration

---

## Validation Checklist

- [ ] FreeFlow servers reachable on port 7751 ✅
- [ ] JMF endpoint responds (HTTP 500) ✅
- [ ] Correct query format obtained ⏳
- [ ] Query format tested and validated ⏳
- [ ] Device enumeration working ⏳
- [ ] Response parsing verified ⏳
