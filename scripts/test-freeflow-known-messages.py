#!/usr/bin/env python3
"""Test KnownMessages capability against FreeFlow Core servers."""

import asyncio
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from app.config import Settings
from app.freeflow_jmf import FreeFlowJmfService, build_known_messages_request


async def test_known_messages():
    """Test KnownMessages against configured FreeFlow servers."""
    settings = Settings()
    service = FreeFlowJmfService(settings)
    
    print("=" * 80)
    print("Testing FreeFlow KnownMessages Capability")
    print("=" * 80)
    
    # Test the request format
    print("\n1. Request Format Test")
    print("-" * 40)
    request_xml = build_known_messages_request()
    print(f"Request length: {len(request_xml)} bytes")
    print(f"Request preview:\n{request_xml[:500].decode('utf-8')}...")
    
    # Test against servers
    print("\n2. Server Capability Test")
    print("-" * 40)
    results = await asyncio.to_thread(service.known_messages)
    
    for result in results:
        print(f"\nServer: {result.name} ({result.role})")
        print(f"  Version: {result.version}")
        print(f"  State: {result.state}")
        print(f"  Detail: {result.detail}")
        
        if result.http_status:
            print(f"  HTTP Status: {result.http_status}")
        
        if result.response_ms:
            print(f"  Response Time: {result.response_ms}ms")
        
        if result.messages:
            print(f"  Supported Message Types ({len(result.messages)}):")
            for msg in result.messages:
                print(f"    - {msg.message_type}")
                if msg.description:
                    print(f"      Description: {msg.description}")
                print(f"      Direction: {msg.direction}, Version: {msg.version}")
        else:
            print("  No message types returned")
    
    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)
    
    return results


if __name__ == "__main__":
    results = asyncio.run(test_known_messages())
    
    # Summary
    healthy_count = sum(1 for r in results if r.state == "healthy")
    total_count = len(results)
    
    print(f"\nSummary: {healthy_count}/{total_count} servers responded successfully")
    
    if healthy_count > 0:
        all_messages = set()
        for result in results:
            if result.state == "healthy":
                for msg in result.messages:
                    all_messages.add(msg.message_type)
        
        print(f"Total unique message types discovered: {len(all_messages)}")
        for msg in sorted(all_messages):
            print(f"  - {msg}")
