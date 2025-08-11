"""Echo and file upload demo using RNS LinkService."""

import time
from typing import Optional

import RNS


class LinkService:
    """Service that echoes packets and stores uploaded files."""

    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize Reticulum and announce the service.

        Args:
            config_path: Optional path to the Reticulum configuration directory.
        """
        self.reticulum = RNS.Reticulum(config_path)
        self.identity = RNS.Identity()
        self.destination = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "linkdemo",
            "service",
        )
        self.destination.set_link_established_callback(self.link_established)
        self.destination.accepts_links(True)
        print("Service hash:", RNS.prettyhexrep(self.destination.hash))
        self.destination.announce()

    def link_established(self, link: RNS.Link) -> None:
        """Configure callbacks for a newly established link.

        Args:
            link: The established link instance.
        """
        print("Link established from", RNS.prettyhexrep(link.remote_identity.hash))
        link.set_packet_callback(self.packet_received)
        link.set_resource_strategy(RNS.Link.ACCEPT_ALL)
        link.set_resource_concluded_callback(self.resource_concluded)

    def packet_received(self, data: bytes, packet: RNS.Packet) -> None:
        """Echo any received data back to the sender.

        Args:
            data: Raw payload received over the link.
            packet: The packet object containing metadata.
        """
        print("Received packet:", data)
        RNS.Packet(packet.link, data).send()

    def resource_concluded(self, resource: RNS.Resource) -> None:
        """Persist a completed resource to disk.

        Args:
            resource: The finished inbound resource.
        """
        filename = f"upload_{RNS.hexrep(resource.hash)}"
        with open(filename, "wb") as handle:
            handle.write(resource.data.read())
        print("Stored file", filename)

    def run(self) -> None:
        """Run the service indefinitely."""
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    LinkService().run()
