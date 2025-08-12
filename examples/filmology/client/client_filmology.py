import asyncio

from reticulum_openapi.client import LXMFClient

from examples.filmology.Server.models_filmology import Movie


async def main() -> None:
    """Send sample movie requests."""
    client = LXMFClient(auth_token="secret")
    server_id = input("Server Identity Hash: ")

    movie = Movie(id=1, title="Example", description="Demo film")
    resp = await client.send_command(
        server_id, "CreateMovie", movie, await_response=True
    )
    print("Create response:", resp)

    retrieved = await client.send_command(
        server_id, "RetrieveMovie", movie.id, await_response=True
    )
    print("Retrieve response:", retrieved)


if __name__ == "__main__":
    asyncio.run(main())
