"""Eventing package for Python.

A pythonic event emitter inspired by Node.js'
EventEmitter and Python's logging libraries.
"""

from __future__ import annotations

__version__ = "0.2.0"

import asyncio
from asyncio import AbstractEventLoop
from collections import defaultdict
import contextlib
from contextvars import ContextVar
from typing import Iterator, Optional
import warnings

from .validation import event_name_validator
from .validation import validate_arguments


class Manager:
    def __init__(self, root_node: EventEmitter):
        self.root = root_node
        self.emitter_dict: dict[str, EventEmitter] = {}

    def get_emitter(self, name: str) -> EventEmitter:
        if not isinstance(name, str):
            raise TypeError("An emitter name must be a string")
        try:
            return self.emitter_dict[name]
        except KeyError:
            emitter = EventEmitter(name)
            self.emitter_dict[name] = emitter
            return emitter


class EventEmitter:
    manager: Manager
    root: RootEmitter
    _deferred_emits_var: ContextVar[list] = ContextVar("deferred_emits")

    def __init__(self, name: str):
        self.name = name
        self._listeners: defaultdict[str, list] = defaultdict(list)
        self._loop: Optional[AbstractEventLoop] = None

    @validate_arguments(event_name_validator)
    def listener_count(self, event_name: str, /) -> int:
        return len(self._listeners[event_name])

    @validate_arguments(event_name_validator)
    def listeners(self, event_name: str, /) -> list[EventEmitter]:
        return self._listeners[event_name]

    @validate_arguments(event_name_validator)
    def add_listener(self, event_name: str, /, listener) -> EventEmitter:
        self._on(event_name, listener)
        return self

    @validate_arguments(event_name_validator)
    def remove_listener(self, event_name: str, /, listener) -> EventEmitter:
        try:
            self._listeners[event_name].remove(listener)
        except ValueError:
            warnings.warn("Attempted to remove listener not present.")
        return self

    @validate_arguments(event_name_validator)
    def emit(self, event_name: str, /, *args, **kwargs) -> bool:
        with self._defer_emits(event_name, args, kwargs) as deferred_emits:
            listeners = self._listeners[event_name].copy()
            # We must store this first's call return value as we might
            # overwrite `listeners`
            return_value = bool(listeners)

            for event_name, args, kwargs in deferred_emits:
                for listener in listeners:
                    self._emit(listener, args, kwargs)
                listeners = self._listeners[event_name].copy()

            # TODO: Check to see if this is actually valid since we defer
            return return_value

    @contextlib.contextmanager
    def _defer_emits(self, event_name, args, kwargs) -> Iterator:
        try:
            deferred_emits = self._deferred_emits_var.get()
        except LookupError:
            # Initial call to emit, setup to catch and handle eventual
            # recursive calls
            deferred_emits = []
            token = self._deferred_emits_var.set(deferred_emits)

            def defer_generator():
                yield event_name, args, kwargs
                try:
                    while True:
                        yield deferred_emits.pop(0)
                except IndexError:
                    return

            # Give this initial caller an iterator that will return the first
            # call and all potential deferred emits to come
            defer_iterator = defer_generator()
        else:
            # We've been recursively called as a result by a listener
            deferred_emits.append((event_name, args, kwargs))
            # Return an empty iterator since we've deferred our emit
            # to be handled by the owner
            defer_iterator = iter(())

        try:
            yield defer_iterator
        finally:
            try:
                self._deferred_emits_var.reset(token)
            except NameError:
                pass

    def _emit(self, listener, args, kwargs):
        if asyncio.iscoroutinefunction(listener):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            coro = listener(*args, **kwargs)
            if loop is None or loop != self._loop:
                asyncio.run_coroutine_threadsafe(coro, self._loop)
            else:
                self._loop.create_task(coro)
        else:
            listener(*args, **kwargs)

    @validate_arguments(event_name_validator)
    def on(self, event_name: str, /):
        def inner(listener):
            self._on(event_name, listener)
            return listener

        return inner

    def _on(self, event_name: str, /, listener):
        self._listeners[event_name].append(listener)

    def set_event_loop(self, loop: AbstractEventLoop):
        self._loop = loop


class RootEmitter(EventEmitter):
    def __init__(self):
        super().__init__("root")


root = RootEmitter()
EventEmitter.root = root
EventEmitter.manager = Manager(root)


def get_emitter(name: str = "") -> EventEmitter:
    if name in ("", root.name):
        return root
    else:
        return EventEmitter.manager.get_emitter(name)
