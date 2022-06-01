import contextvars
import dis
from functools import wraps
import inspect
import itertools
import sys
import traceback
import warnings

RESET = "\x1b[0m"
RED = "\x1b[31m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
BLUE = "\x1b[34m"


class Emitter:
    _class_listeners = contextvars.ContextVar("class_listeners")
    listeners = []

    def __new__(cls, *args, **kwargs):
        raise RuntimeError(f"{cls} should not be instantiated")

    @classmethod
    def mark(cls, class_to_wrap):
        try:
            class_listeners = cls._class_listeners.get()
        except LookupError:
            warnings.warn("magic wrapped class without any listeners to setup")
            return class_to_wrap
        else:
            token = class_listeners.pop(0)
            cls._class_listeners.reset(token)

        instance_listeners = []
        for method_name, method_type in class_listeners:
            # Instance methods need to be delayed until instantiation.
            if method_type == "instance":
                instance_listeners.append(method_name)
                continue

            if method_type not in ["class", "static"]:
                raise ValueError(
                    f"method type must be one of: instance | class | static; got {method_type}"
                )

            # What we get now will be bound, if necessary, since the class
            # has been fully constructed.
            listener = getattr(class_to_wrap, method_name)
            cls.listeners.append(listener)

        if instance_listeners:
            setattr(
                class_to_wrap,
                "__init__",
                cls._add_instance_listeners(
                    class_to_wrap, tuple(instance_listeners)
                ),
            )

        return class_to_wrap

    @classmethod
    def _add_instance_listeners(cls, class_to_wrap, instance_listeners):
        try:
            __init__ = vars(class_to_wrap)["__init__"]
        except KeyError:

            def __dummy_init__(self, *args, **kwargs):
                super(class_to_wrap.__mro__[0], self).__init__(*args, **kwargs)

            __init__ = __dummy_init__

        @wraps(__init__)
        def wrapper(self, *args, **kwargs):
            __init__(self, *args, **kwargs)
            for name in instance_listeners:
                instance_listener = getattr(self, name)
                cls.listeners.append(instance_listener)

        return wrapper

    class NotAClassError(Exception):
        pass

    @classmethod
    def on(cls, f):
        frame = inspect.currentframe()
        try:
            current_code = frame.f_back.f_code
            scope = frame.f_back.f_back
            if scope is None:
                raise cls.NotAClassError

            current_offset = scope.f_lasti
            instructions = [
                instr
                for instr in dis.get_instructions(scope.f_code)
                if instr.offset < current_offset
            ][::-1]

            for idx, instr in enumerate(instructions):
                if instr.argval is current_code:
                    # verify that we're indeed building a class
                    if instructions[idx + 1].opname == "LOAD_BUILD_CLASS":
                        # We've confirmed that we're part of a class
                        load_build_class_idx = idx + 1
                        break
            else:
                raise cls.NotAClassError

            # Verify that the class is marked so that the listeners actually gets added
            instructions = [
                *itertools.takewhile(
                    lambda x: not x.opname.startswith("STORE_"),
                    instructions[load_build_class_idx + 1:],
                )
            ][::-1]
            tos = None
            for instr in instructions:
                if instr.opname == "LOAD_NAME":
                    try:
                        obj = scope.f_locals[instr.argval]
                    except KeyError:
                        obj = scope.f_globals[instr.argval]

                    if obj == cls.mark:
                        break
                    else:
                        tos = obj
                elif instr.opname == "LOAD_ATTR":
                    obj = getattr(tos, instr.argval)
                    if obj == cls.mark:
                        break
                    else:
                        tos = obj
            else:
                raise RuntimeError(
                    "@Emitter.on used on class methods without marking the class with @Emitter.mark"
                )

            scope = frame.f_back
            current_offset = scope.f_lasti
            instructions = list(dis.get_instructions(scope.f_code))
            partition_idx = next(
                idx
                for idx, instr in enumerate(instructions)
                if instr.offset == current_offset
            )
            # get the method_type
            method_type = None
            for instr in reversed(instructions[:partition_idx]):
                if instr.opname == "LOAD_NAME":
                    if instr.argval == "classmethod":
                        method_type = "class"
                    elif instr.argval == "staticmethod":
                        method_type = "static"
                if instr.opname.startswith("STORE_"):
                    method_type = "instance"
                if method_type is not None:
                    break

            method_name = None
            for instr in instructions[partition_idx:]:
                if instr.opname == "STORE_NAME":
                    method_name = instr.argval
                    break

            try:
                class_listeners = cls._class_listeners.get()
            except LookupError:
                class_listeners = []
                token = cls._class_listeners.set(class_listeners)
                class_listeners.append(token)

            class_listeners.append((method_name, method_type))
        except cls.NotAClassError:
            # Just add it straight up
            cls.listeners.append(f)
        finally:
            del frame

        return f


@Emitter.on
def unknown(*args):
    return args


@Emitter.mark
class Test:
    @classmethod
    @Emitter.on
    def class_method(cls, *args):
        return cls, *args

    extra_class_method = classmethod(Emitter.on(unknown))

    @staticmethod
    @Emitter.on
    def static_method(*args):
        return args

    extra_static_method = staticmethod(Emitter.on(unknown))

    @Emitter.on
    def instance_method(self, *args):
        return self, *args

    extra_instance_method = Emitter.on(unknown)


if __name__ == "__main__":
    try:
        Emitter._class_listeners.get()
        assert False
    except LookupError:
        pass

    listeners = Emitter.listeners
    assert len(listeners) == 5
    t = Test()
    assert len(listeners) == 7
    funcs = [
        # Note that order here is hardcoded. Free, class and static are added
        # in order of appearance but instance first when instantiated
        (unknown, listeners[0], "free"),
        ("class_method", listeners[1], "class"),
        ("extra_class_method", listeners[2], "class"),
        ("static_method", listeners[3], "static"),
        ("extra_static_method", listeners[4], "static"),
        ("instance_method", listeners[5], "instance"),
        ("extra_instance_method", listeners[6], "instance"),
    ]

    for func_name, listener, arg in funcs:
        print("-------------------------------------")
        try:
            if isinstance(func_name, str):
                func = getattr(t, func_name)
            else:
                func = func_name
                func_name = func_name.__name__
            func_ret = func(arg)
            listener_ret = listener(arg)
            assert func_ret == listener_ret, "Return values should be same"
        except (TypeError, AssertionError):
            print(f"{RED}[FAILED]{RESET} {func_name}: function_type '{arg}'")
            print(RED, *traceback.format_exception(*sys.exc_info()), RESET)
        else:
            print(f"{GREEN}[PASSED]{RESET} {func_name}: function_type '{arg}'")
