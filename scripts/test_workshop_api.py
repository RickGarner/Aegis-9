#!/usr/bin/env python
"""Test Workshop Desktop local model API."""

import httpx
import asyncio


async def main():
    base_url = "http://127.0.0.1:44245"
    
    print("Testing Workshop Desktop local model API...")
    
    # Test models endpoint
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{base_url}/v1/models")
            print(f"\n1. Models endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Models response: {data}")
            else:
                print(f"   Error: {response.text[:500]}")
    except Exception as e:
        print(f"\n1. Models endpoint error: {e}")
    
    # Test chat endpoint with a simple query
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "model": "llama-server",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Return AEGIS_WORKSHOP_OK"}
                ],
                "stream": False
            }
            response = await client.post(f"{base_url}/v1/chat/completions", json=payload)
            print(f"\n2. Chat endpoint: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response content: {data.get('choices', [{}])[0].get('message', {}).get('content', '')}")
            else:
                print(f"   Error: {response.text[:500]}")
    except Exception as e:
        print(f"\n2. Chat endpoint error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
