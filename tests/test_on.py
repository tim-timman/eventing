import pytest

import eventing


@pytest.fixture
def ee():
    return eventing.get_emitter()


def test_listener_with_on_decorator_is_added_to_listeners(ee):
    @ee.on("foo")
    def listener():
        pass

    assert ee.listeners("foo") == [listener]


def test_decorating_function_twice_adds_listener_twice(ee):
    @ee.on("foo")
    @ee.on("foo")
    def listener():
        pass

    assert ee.listeners("foo") == [listener, listener]
