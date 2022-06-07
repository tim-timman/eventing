import asyncio
from unittest.mock import AsyncMock

import pytest

import eventing

REAL_LOOP = 1
FAKE_LOOP = 2
NO_LOOP = 3


@pytest.mark.parametrize(
    ("emitter_loop_pairs", "emit_on"),
    (
        ((("foo", REAL_LOOP),), "foo"),
        ((("", REAL_LOOP), ("foo", NO_LOOP), ("foo.bar.baz", NO_LOOP)), "foo.bar.baz"),
        (
            (
                ("foo.bar.baz", NO_LOOP),
                ("foo.bar", NO_LOOP),
                ("foo", REAL_LOOP),
                ("", FAKE_LOOP),
            ),
            "foo.bar",
        ),
    ),
)
@pytest.mark.asyncio
async def test_emitter_should_use_nearest_loop_in_parents_if_not_set_on_self(
    event_loop,
    emitter_loop_pairs,
    emit_on,
):
    for emitter_name, loop in emitter_loop_pairs:
        tmp_ee = eventing.get_emitter(emitter_name)
        if loop == REAL_LOOP:
            tmp_ee.set_event_loop(event_loop)
        elif loop == FAKE_LOOP:
            tmp_ee.set_event_loop(asyncio.new_event_loop())
        elif loop == NO_LOOP:
            pass

    ee = eventing.get_emitter(emit_on)

    mock = AsyncMock(return_value=None)
    ee.add_listener("an_event", mock)

    ee.emit("an_event")

    # Allow the listener to run
    await asyncio.sleep(0)

    mock.assert_awaited_once_with()
