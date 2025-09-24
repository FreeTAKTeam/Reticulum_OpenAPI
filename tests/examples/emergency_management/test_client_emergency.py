"""Tests for the interactive Emergency Management client helpers."""

from __future__ import annotations

import asyncio
import builtins

import pytest


from examples.EmergencyManagement.client import client_emergency


class _DummyLoop:
    """Test double that records executor invocations."""

    def __init__(self) -> None:
        self.calls = []

    async def run_in_executor(self, executor, func, *args):
        """Record calls and invoke the provided function synchronously."""

        self.calls.append((executor, func, args))
        return func(*args)


@pytest.mark.asyncio
async def test_prompt_for_server_identity_uses_executor_and_strips(monkeypatch):
    """The server identity prompt should run via an executor and trim whitespace."""

    dummy_loop = _DummyLoop()
    monkeypatch.setattr(asyncio, "get_running_loop", lambda: dummy_loop)

    prompts = {}

    def fake_input(prompt: str) -> str:
        prompts["value"] = prompt
        return " 0123456789ABCDEF "

    monkeypatch.setattr(builtins, "input", fake_input)

    response = await client_emergency._prompt_for_server_identity()

    assert response == "0123456789ABCDEF"
    assert dummy_loop.calls == [
        (None, fake_input, (client_emergency.PROMPT_MESSAGE,)),
    ]
    assert prompts["value"] == client_emergency.PROMPT_MESSAGE


@pytest.mark.asyncio
async def test_wait_until_interrupted_respects_external_event():
    """The interruption helper should exit once the provided event is set."""

    stop_event = asyncio.Event()
    wait_task = asyncio.create_task(
        client_emergency._wait_until_interrupted(stop_event=stop_event)
    )
    await asyncio.sleep(0)
    stop_event.set()
    await asyncio.wait_for(wait_task, timeout=0.1)
