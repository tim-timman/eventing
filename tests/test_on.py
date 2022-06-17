import asyncio
from unittest.mock import call

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


def test_instancemethod_decorated_with_on_isnt_added_until_instantiated(ee):
    @ee.handle_methods
    class Foo:
        @ee.on("foo", method=True)
        def listener(self):
            pass

    assert ee.listeners("foo") == []
    foo_instance = Foo()
    assert ee.listeners("foo") == [foo_instance.listener]


def test_instancemethod_decorated_with_on_is_correctly_bound_when_called(ee):
    mock_calls = []

    @ee.handle_methods
    class Foo:
        @ee.on("foo", method=True)
        def listener(self):
            mock_calls.append(call(self))

    foo_instance = Foo()
    ee.emit("foo")
    assert mock_calls == [call(foo_instance)]


def test_classmethod_decorated_with_on_is_correctly_bound_when_called(ee):
    mock_calls = []

    @ee.handle_methods
    class Foo:
        @classmethod
        @ee.on("foo", method=True)
        def listener(cls):
            mock_calls.append(call(cls))

    assert ee.listeners("foo") == [Foo.listener]
    ee.emit("foo")
    assert mock_calls == [call(Foo)]


def test_staticmethod_decorated_with_on_is_correctly_called(ee):
    mock_calls = []

    @ee.handle_methods
    class Foo:
        @staticmethod
        @ee.on("foo", method=True)
        def listener():
            mock_calls.append(call())

    assert ee.listeners("foo") == [Foo.listener]
    ee.emit("foo")
    assert mock_calls == [call()]


def test_should_warn_if_class_is_wrapped_without_method_listeners(ee):
    with pytest.warns(UserWarning):

        @ee.handle_methods
        class Foo:
            pass


def test_should_error_if_method_listener_by_no_class_deco(ee):
    with pytest.raises(eventing.MissingClassMethodHandler):

        class Foo:
            @ee.on("foo", method=True)
            def listener(self):
                pass


def test_should_error_if_method_listener_without_class(ee):
    with pytest.raises(ValueError):

        @ee.on("foo", method=True)
        def listener():
            pass


def test_function_reuse_through_descriptor_methods_correctly_added_and_called(ee):
    mock_calls = []

    def mock(*args):
        mock_calls.append(call(*args))

    def bad(*args):
        raise AssertionError("Not supposed to be called")

    foo_deco = ee.on("foo", method=True)

    @ee.handle_methods
    class Foo:
        non_deco_method = bad
        instance_method = foo_deco(mock)
        class_method = classmethod(foo_deco(mock))
        static_method = staticmethod(foo_deco(mock))

    assert ee.listeners("foo") == [Foo.class_method, Foo.static_method]
    instance = Foo()
    assert ee.listeners("foo") == [
        Foo.class_method,
        Foo.static_method,
        instance.instance_method,
    ]
    ee.emit("foo")
    assert mock_calls == [call(Foo), call(), call(instance)]


@pytest.mark.asyncio
async def test_async_class_method_variants_correctly_added_and_called(ee, event_loop):
    ee.set_event_loop(event_loop)

    async_mock_calls = []

    async def async_mock(*args):
        async_mock_calls.append(call(*args, "mock"))

    async def bad(*args):
        raise AssertionError("Not supposed to be called")

    foo_deco = ee.on("foo", method=True)

    @ee.handle_methods
    class Foo:
        non_deco_dec_method = bad
        instance_desc_method = foo_deco(async_mock)
        class_desc_method = classmethod(foo_deco(async_mock))
        static_desc_method = staticmethod(foo_deco(async_mock))

        async def non_deco_method(self):
            raise AssertionError("Not supposed to be called")

        @ee.on("foo", method=True)
        async def instance_method(self):
            async_mock_calls.append(call(self))

        @classmethod
        @ee.on("foo", method=True)
        async def class_method(cls):
            async_mock_calls.append(call(cls))

        @staticmethod
        @ee.on("foo", method=True)
        async def static_method():
            async_mock_calls.append(call())

    instance = Foo()
    ee.emit("foo")
    # Just to allow other queued coroutines to run
    await asyncio.sleep(0)
    assert async_mock_calls == [
        call(Foo, "mock"),
        call("mock"),
        call(Foo),
        call(),
        call(instance, "mock"),
        call(instance),
    ]
