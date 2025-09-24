"""Utilities for generating and seeding random Emergency Management events."""

from __future__ import annotations

import random
import time
from dataclasses import replace
from datetime import datetime, timezone
from typing import Callable, List, Optional, Sequence

from examples.EmergencyManagement.Server.models_emergency import (
    Detail,
    EmergencyActionMessage,
    Event,
    Point,
)
from examples.EmergencyManagement.client.client import create_event
from examples.EmergencyManagement.client.eam_test import generate_random_eam

# Reason: The helper mirrors ``eam_test`` but encapsulates the behaviour inside a
# class so that the CLI can seed events with deterministic injection during
# testing.


HowValues = Sequence[str]


class RandomEventSeeder:
    """Generate random :class:`Event` payloads and send them to the server."""

    _HOW_VALUES: HowValues = (
        "m-g",
        "h-g",
        "a-f",
        "a-u",
    )
    _TYPE_VALUES: Sequence[str] = (
        "a-h-G-U-C",
        "a-h-H",
        "a-h-E",
    )
    _ACCESS_VALUES: Sequence[str] = (
        "Public",
        "Restricted",
        "Private",
    )

    def __init__(
        self,
        client,
        server_identity: str,
        *,
        count: int = 5,
        random_generator: Optional[random.Random] = None,
        eam_factory: Callable[[], EmergencyActionMessage] = generate_random_eam,
    ) -> None:
        """Initialise the seeder.

        Args:
            client: Configured LXMF client used to send commands.
            server_identity (str): Destination identity hash for the LXMF server.
            count (int): Number of events to seed when :meth:`seed` is invoked.
            random_generator (Optional[random.Random]): Optional deterministic
                generator to make testing reproducible.
            eam_factory (Callable[[], EmergencyActionMessage]): Factory that
                returns random emergency action messages. Defaults to
                :func:`generate_random_eam`.
        """

        if count <= 0:
            raise ValueError("count must be greater than zero")

        self._client = client
        self._server_identity = server_identity
        self._count = count
        self._random = random_generator or random.Random()
        self._eam_factory = eam_factory
        self._generated_uids: set[int] = set()

    def _random_choice(self, values: Sequence[str]) -> Optional[str]:
        """Return a random element from ``values`` or ``None`` when empty."""

        if not values:
            return None
        return self._random.choice(values)

    def _random_uid(self) -> int:
        """Return a unique positive identifier for an event."""

        while True:
            candidate = self._random.randint(1, 9_999_999)
            if candidate not in self._generated_uids:
                self._generated_uids.add(candidate)
                return candidate

    def _random_point(self) -> Optional[Point]:
        """Return a random :class:`Point` or ``None`` if omitted."""

        if self._random.random() < 0.2:
            return None

        return Point(
            lat=self._round_coordinate(self._random.uniform(-90.0, 90.0)),
            lon=self._round_coordinate(self._random.uniform(-180.0, 180.0)),
            ce=self._round_distance(self._random.uniform(0.0, 500.0)),
            le=self._round_distance(self._random.uniform(0.0, 500.0)),
            hae=self._round_distance(self._random.uniform(-100.0, 500.0)),
        )

    def _round_coordinate(self, value: float) -> float:
        """Round coordinate values to six decimal places."""

        return float(f"{value:.6f}")

    def _round_distance(self, value: float) -> float:
        """Round distance values to two decimal places."""

        return float(f"{value:.2f}")

    def _random_detail(self) -> Optional[Detail]:
        """Return a random :class:`Detail` payload."""

        if self._random.random() < 0.3:
            return None

        eam = self._eam_factory()
        return Detail(emergencyActionMessage=replace(eam))

    def generate_random_event(self) -> Event:
        """Return a randomly populated :class:`Event`."""

        timestamp = int(time.time())
        stale_time = datetime.now(timezone.utc).isoformat()
        start_time = datetime.now(timezone.utc).isoformat()
        detail = self._random_detail()
        point = self._random_point()
        return Event(
            uid=self._random_uid(),
            how=self._random_choice(self._HOW_VALUES),
            version=self._random.randint(1, 5),
            time=timestamp,
            type=self._random_choice(self._TYPE_VALUES),
            stale=stale_time,
            start=start_time,
            access=self._random_choice(self._ACCESS_VALUES),
            opex=self._random.randint(1, 10),
            qos=self._random.randint(1, 10),
            detail=detail,
            point=point,
        )

    async def send_random_event(self) -> Optional[Event]:
        """Generate and send a random event to the server."""

        event = self.generate_random_event()
        try:
            created_event = await create_event(
                self._client,
                self._server_identity,
                event,
            )
        except TimeoutError as exc:
            print(
                f"Event creation timed out for uid {event.uid}: {exc}",
            )
            return None
        except Exception as exc:  # pragma: no cover - defensive logging
            print(f"Failed to create event for uid {event.uid}: {exc}")
            return None
        return created_event

    async def seed(self) -> List[Event]:
        """Create multiple random events on the server."""

        created: List[Event] = []
        for _ in range(self._count):
            result = await self.send_random_event()
            if result is not None:
                created.append(result)
        return created


__all__ = ["RandomEventSeeder"]
