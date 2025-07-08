import asyncio
from reticulum_openapi.client import LXMFClient
from model import *

async def main():
    client = LXMFClient()
    server_id = input("Server Identity Hash: ")
    payload = None
    response = await client.send_command(server_id, "", payload, await_response=True)
    print("Response:", response)

if __name__ == "__main__":
    asyncio.run(main())
