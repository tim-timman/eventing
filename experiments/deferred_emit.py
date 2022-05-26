"""Experiment with writing a deferred emit.

Aim to find an implementation not changing the call signature but while
avoiding RecursionError in case a listener itself emits an event.
"""

import inspect
import sys
import threading
import timeit
import traceback


class Emitter:
    def __init__(self):
        self._listeners = []

    def emit(self, *args, **kwargs):
        raise NotImplementedError()

    def add_listener(self, listener):
        self._listeners.append(listener)


class PatchDeferredEmitter(Emitter):
    """Implements deferred emits by means of patching"""
    def emit(self, *args, **kwargs):
        # Use helper function to make sure it's always the same entry
        # we patch. This way, even if `emit(...)` was bound by the caller
        # to a variable of different name or whatever, the patch still
        # applies.
        self._emit(*args, **kwargs)

    def _emit(self, *args, **kwargs):
        deferred_emits = []

        def defer(*_args, **_kwargs):
            deferred_emits.append((_args, _kwargs))

        original = self._emit
        try:
            # Patch the emit function
            self._emit = defer

            # copy the current listeners as it may be modified as part of calling them
            listeners = self._listeners.copy()
            while True:
                for listener in listeners:
                    listener(*args, **kwargs)
                try:
                    args, kwargs = deferred_emits.pop(0)
                except IndexError:
                    break
                else:
                    # create new listeners
                    listeners = self._listeners.copy()
        finally:
            # Set it back to normal
            self._emit = original


class ThreadingLocalDeferredEmitter(Emitter):
    """Implements deferred emits by use of threading.local storage"""
    def __init__(self):
        super().__init__()
        self._data = threading.local()

    def emit(self, *args, **kwargs):
        try:
            deferred_emits = self._data.deferred_emits
        except AttributeError:
            # This means this is the first call to emit
            deferred_emits = self._data.deferred_emits = []
        else:
            # This means we were recursively called
            deferred_emits.append((args, kwargs))
            return

        # copy the current listeners as it may be modified as part of calling them
        listeners = self._listeners.copy()
        while True:
            for listener in listeners:
                listener(*args, **kwargs)
            try:
                args, kwargs = deferred_emits.pop(0)
            except IndexError:
                del self._data.deferred_emits
                return
            else:
                # create new listeners
                listeners = self._listeners.copy()


class IntrospectiveDeferredEmitter(Emitter):
    """Implements deferred emits by use of stack introspection"""
    def emit(self, *args, **kwargs):
        deferred_emits = []
        frame = inspect.currentframe()
        try:
            frame = frame
            self_name = frame.f_code.co_name
            while frame := frame.f_back:
                if frame.f_code.co_name == self_name:
                    frame.f_locals["deferred_emits"].append((args, kwargs))
                    return
        finally:
            del frame

        # copy the current listeners as it may be modified as part of calling them
        listeners = self._listeners.copy()
        while True:
            for listener in listeners:
                listener(*args, **kwargs)
            try:
                args, kwargs = deferred_emits.pop(0)
            except IndexError:
                return
            else:
                # create new listeners
                listeners = self._listeners.copy()


GREEN = "\x1b[32m"
RED = "\x1b[31m"
RESET = "\x1b[0m"


def test(emitter_cls: type[Emitter]):
    _callback_called = 0

    def recurse_emit_listener(i):
        nonlocal _callback_called
        _callback_called += 1
        i -= 1
        if i > 0:
            ee.emit(i)

    ee = emitter_cls()
    ee.add_listener(recurse_emit_listener)

    try:
        num = 20000
        ee.emit(num)
        assert _callback_called == num, f"Callback called {_callback_called} time, expected {num}"
    except Exception:
        print(RED, *traceback.format_exception(*sys.exc_info()), RESET)
        print(f"{RED}[FAILED]{RESET} {emitter_cls.__name__}")
    else:
        print(f"{GREEN}[PASSED]{RESET} {emitter_cls.__name__}")
        num_calls = 100
        time_taken = timeit.timeit("ee.emit(num)", globals={**globals(), **locals()}, number=num_calls)
        print(f"    Avg. time/call: {round(time_taken/num_calls * 1000, 3)} ms")
    print("---------------------------------------")


if __name__ == "__main__":
    test(PatchDeferredEmitter)
    test(ThreadingLocalDeferredEmitter)
    test(IntrospectiveDeferredEmitter)
