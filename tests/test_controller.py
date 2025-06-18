import pytest
import asyncio

from reticulum_openapi import controller as c

@pytest.mark.asyncio
async def test_handle_exceptions_success():
    @c.handle_exceptions
    async def handler(self, x):
        return x * 2

    result = await handler(object(), 3)
    assert result == 6

@pytest.mark.asyncio
async def test_handle_exceptions_apierror():
    @c.handle_exceptions
    async def handler(self):
        raise c.APIException("bad", 400)

    result = await handler(object())
    assert result == {"error": "bad", "code": 400}

@pytest.mark.asyncio
async def test_handle_exceptions_generic():
    @c.handle_exceptions
    async def handler(self):
        raise ValueError("boom")

    result = await handler(object())
    assert result == {"error": "InternalServerError", "code": 500}

@pytest.mark.asyncio
async def test_run_business_logic(monkeypatch):
    ctrl = c.Controller()
    async def logic(a, b):
        return a + b
    result = await ctrl.run_business_logic(logic, 2, 3)
    assert result == 5

@pytest.mark.asyncio
async def test_run_business_logic_error():
    ctrl = c.Controller()
    async def logic():
        raise c.APIException("fail", 401)
    result = await ctrl.run_business_logic(logic)
    assert result == {"error": "fail", "code": 401}
