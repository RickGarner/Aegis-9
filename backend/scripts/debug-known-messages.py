#!/usr/bin/env python3
"""Debug KnownMessages response format."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.config import Settings
from app.freeflow_jmf import FreeFlowJmfService, build_known_messages_request
import httpx


def debug_known_messages():
    """Debug KnownMessages response."""
    settings = Settings()
    service = FreeFlowJmfService(settings)
    
    print("=" * 80)
    print("Debug KnownMessages Response")
    print("=" * 80)
    
    # Load inventory
    import json
    payload = json.loads(service._inventory_path.read_text(encoding="utf-8"))
    
    for item in payload:
        if not isinstance(item, dict) or not item.get("enabled", True):
            continue
        
        name = item.get("name", "Unknown")
        url = item.get("jmfUrl", "").strip()
        
        if not url:
            continue
        
        print(f"\n{'=' * 80}")
        print(f"Server: {name}")
        print(f"URL: {url}")
        print(f"{'=' * 80}")
        
        # Send request
        response = httpx.post(
            url,
            content=build_known_messages_request(),
            headers={"Content-Type": "application/vnd.cip4-jmf+xml"},
            timeout=30,
        )
        
        print(f"\nHTTP Status: {response.status_code}")
        print(f"\nRaw Response ({len(response.content)} bytes):")
        print("-" * 40)
        print(response.text[:2000])
        if len(response.text) > 2000:
            print(f"\n... ({len(response.text) - 2000} more bytes)")
        
        print("\n" + "-" * 40)
        print("XML Structure Analysis:")
        print("-" * 40)
        
        import xml.etree.ElementTree as ET
        try:
            root = ET.fromstring(response.content)
            print(f"Root tag: {root.tag}")
            print(f"Root attributes: {dict(root.attrib)}")
            
            print(f"\nAll elements in response:")
            for elem in root.iter():
                tag_name = elem.tag.rsplit("}", 1)[-1]
                print(f"  - {tag_name}: {dict(elem.attrib) if elem.attrib else '(no attrs)'}")
                if elem.text and elem.text.strip():
                    print(f"      Text: {elem.text.strip()[:100]}")
        except ET.ParseError as e:
            print(f"XML Parse Error: {e}")


if __name__ == "__main__":
    debug_known_messages()
