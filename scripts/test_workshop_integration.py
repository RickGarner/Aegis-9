#!/usr/bin/env python
"""Test Workshop integration with Aegis-9 chat endpoint."""

import httpx
import json


async def test_workshop_chat():
    """Test the Workshop integration via the /api/chat endpoint."""
    
    print("Testing Workshop integration with Aegis-9...")
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # Test 1: Check Workshop status
        print("\n1. Testing /api/workshop/status...")
        response = await client.get("http://localhost:8000/api/workshop/status")
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"   Provider: {data.get('provider')}")
            print(f"   Model: {data.get('model')}")
            print(f"   Location: {data.get('location')}")
            print(f"   Status: {data.get('status')}")
            print(f"   Detail: {data.get('detail')}")
        else:
            print(f"   Error: {response.text}")
            return
        
        # Test 2: Send a simple chat request
        print("\n2. Testing /api/chat with Workshop...")
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Return AEGIS_WORKSHOP_INTEGRATION_OK"}
        ]
        
        try:
            response = await client.post(
                "http://localhost:8000/api/chat",
                json={"messages": messages},
                timeout=30.0
            )
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Model: {data.get('model')}")
                print(f"   Provider: {data.get('provider')}")
                print(f"   Location: {data.get('location')}")
                content = data.get('content', '')
                print(f"   Content preview: {content[:200]}...")
                if "AEGIS_WORKSHOP_INTEGRATION_OK" in content:
                    print("   ✓ SUCCESS: Workshop integration working correctly!")
                else:
                    print("   ✗ WARNING: Unexpected response content")
            else:
                print(f"   Error: {response.text}")
        except Exception as e:
            print(f"   Error: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_workshop_chat())
