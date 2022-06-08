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
    called_arg = None

    @ee.handle_methods
    class Foo:
        @ee.on("foo", method=True)
        def listener(self):
            nonlocal called_arg
            called_arg = self

    foo_instance = Foo()
    ee.emit("foo")
    assert called_arg == foo_instance


def test_classmethod_decorated_with_on_is_correctly_bound_when_called(ee):
    called_arg = None

    @ee.handle_methods
    class Foo:
        @classmethod
        @ee.on("foo", method=True)
        def listener(cls):
            nonlocal called_arg
            called_arg = cls

    assert ee.listeners("foo") == [Foo.listener]
    ee.emit("foo")
    assert called_arg == Foo


def test_staticmethod_decorated_with_on_is_correctly_called(ee):
    called = False

    @ee.handle_methods
    class Foo:
        @staticmethod
        @ee.on("foo", method=True)
        def listener():
            nonlocal called
            called = True

    assert ee.listeners("foo") == [Foo.listener]
    ee.emit("foo")
    assert called


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
