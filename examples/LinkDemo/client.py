"""Client for the LinkService demo."""

import os
import sys
import time
from typing import Optional

import RNS


def on_link(link: RNS.Link, file_path: Optional[str]) -> None:
    """Send a ping and optionally upload a file once the link is ready.

    Args:
        link: Established link to the server.
        file_path: Path to a file to upload. If ``None``, no file is sent.
    """
    print("Link established")
    link.set_packet_callback(lambda data, packet: print("Echo:", data))
    RNS.Packet(link, b"hello").send()
    if file_path and os.path.exists(file_path):
        with open(file_path, "rb") as handle:
            RNS.Resource(handle, link)
    else:
        print("No file uploaded")


def main(dest_hex: str, file_path: Optional[str] = None) -> None:
    """Connect to the server and demonstrate link usage.

    Args:
        dest_hex: Hexadecimal hash of the server destination.
        file_path: Optional path to a file to upload.
    """
    RNS.Reticulum()
    dest_hash = bytes.fromhex(dest_hex)
    dest = RNS.Destination(
        dest_hash,
        RNS.Destination.OUT,
        RNS.Destination.SINGLE,
        "linkdemo",
        "service",
    )
    RNS.Link(dest, established_callback=lambda link: on_link(link, file_path))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python client.py <server_hash> [file]")
    else:
        main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
