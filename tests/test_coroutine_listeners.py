import asyncio
from unittest.mock import AsyncMock

import pytest

import eventing


@pytest.fixture
def ee():
    return eventing.get_emitter()


@pytest.fixture
def add_async_mock_listener(ee):
    def _add_async_mock_listener(event_name):
        mock_listener = AsyncMock(return_value=None)
        ee.add_listener(event_name, mock_listener)
        return mock_listener

    return _add_async_mock_listener


@pytest.mark.asyncio
async def test_coroutine_listener_called(ee, add_async_mock_listener):
    async_foo_listener = add_async_mock_listener("foo")
    ee.emit("foo")
    # Just to allow other queued coroutines to run
    await asyncio.sleep(0)
    async_foo_listener.assert_awaited_once_with()
