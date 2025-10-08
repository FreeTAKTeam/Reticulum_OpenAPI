"""Helpers for Reticulum destination announcements."""

from __future__ import annotations

import logging
from typing import Optional
from typing import Union

import RNS

from .logging_config import configure_logging


configure_logging()
logger = logging.getLogger(__name__)


class DestinationAnnouncer:
    """Create and announce Reticulum destinations for a given identity."""

    def __init__(
        self,
        identity: RNS.Identity,
        application: str,
        aspect: str,
        *,
        direction: Optional[int] = None,
        destination_type: Optional[int] = None,
        app_data: Optional[Union[bytes, str]] = None,
    ) -> None:
        """Initialise the announcer with destination metadata.

        Args:
            identity (RNS.Identity): Identity used for the destination.
            application (str): Application component of the destination name.
            aspect (str): Aspect component of the destination name.
            direction (Optional[int]): Override for the Reticulum destination
                direction. Defaults to ``RNS.Destination.IN``.
            destination_type (Optional[int]): Override for the Reticulum
                destination type. Defaults to ``RNS.Destination.SINGLE``.
            app_data (Optional[Union[bytes, str]]): Metadata transmitted with
                the announce packet. Strings are encoded as UTF-8 prior to
                assignment. Defaults to ``None``.

        Raises:
            ValueError: If ``identity`` is ``None``.
        """

        if identity is None:
            raise ValueError("Identity must be provided for destination announcements")

        self.identity = identity
        self.application = application
        self.aspect = aspect
        self.direction = direction if direction is not None else RNS.Destination.IN
        self.destination_type = (
            destination_type if destination_type is not None else RNS.Destination.SINGLE
        )
        self.destination = RNS.Destination(
            identity,
            self.direction,
            self.destination_type,
            application,
            aspect,
        )
        if isinstance(app_data, str):
            app_data_bytes: Optional[bytes] = app_data.encode("utf-8")
        else:
            app_data_bytes = app_data
        if app_data_bytes is not None:
            self.destination.default_app_data = app_data_bytes

    def announce(self) -> bytes:
        """Send an announce packet for the configured destination.

        Returns:
            bytes: The destination hash that was announced.
        """

        try:
            self.destination.announce()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Destination announcement failed: %s", exc)
            raise
        return self.destination.hash
