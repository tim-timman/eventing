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


METHODS_ON_CLASS_SKIP_REASON = (
    "Wishful functionality; might not be a good idea"
)


@pytest.mark.skip(METHODS_ON_CLASS_SKIP_REASON)
def test_instancemethod_decorated_with_on_isnt_added_until_instantiated(ee):
    class Foo:
        @ee.on("foo")
        def listener(self):
            pass

    assert ee.listeners("foo") == []
    foo_instance = Foo()
    assert ee.listeners("foo") == [foo_instance.listener]


@pytest.mark.skip(METHODS_ON_CLASS_SKIP_REASON)
def test_instancemethod_decorated_with_on_is_correctly_bound_when_called(ee):
    called_arg = None

    class Foo:
        @ee.on("foo")
        def listener(self):
            nonlocal called_arg
            called_arg = self

    foo_instance = Foo()
    ee.emit("foo")
    assert called_arg == foo_instance


@pytest.mark.skip(METHODS_ON_CLASS_SKIP_REASON)
def test_classmethod_decorated_with_on_is_correctly_bound_when_called(ee):
    called_arg = None

    class Foo:
        @classmethod
        @ee.on("foo")
        def listener(cls):
            nonlocal called_arg
            called_arg = cls

    assert ee.listeners("foo") == [Foo.listener]
    ee.emit("foo")
    assert called_arg == Foo


@pytest.mark.skip(METHODS_ON_CLASS_SKIP_REASON)
def test_staticmethod_decorated_with_on_is_correctly_called(ee):
    called = False

    class Foo:
        @staticmethod
        @ee.on("foo")
        def listener():
            nonlocal called
            called = True

    assert ee.listeners("foo") == [Foo.listener]
    ee.emit("foo")
    assert called
