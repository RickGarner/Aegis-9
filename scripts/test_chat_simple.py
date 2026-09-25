#!/usr/bin/env python
"""Simple test of Workshop chat endpoint."""

import httpx
import asyncio


async def main():
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/api/chat",
            json={
                "messages": [
                    {"role": "user", "content": "Hello"}
                ]
            }
        )
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Model: {data.get('model')}")
            print(f"Provider: {data.get('provider')}")
            print(f"Content: {data.get('content', '')[:200]}")
        else:
            print(f"Error: {response.text}")


if __name__ == "__main__":
    asyncio.run(main())
