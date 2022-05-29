"""Eventing package for Python.

A pythonic event emitter inspired by Node.js'
EventEmitter and Python's logging libraries.
"""

from __future__ import annotations

__version__ = "0.1.0"

import asyncio
from collections import defaultdict
from contextvars import ContextVar
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

    @validate_arguments(event_name_validator)
    def listener_count(self, event_name: str, /) -> int:
        return len(self._listeners[event_name])

    @validate_arguments(event_name_validator)
    def listeners(self, event_name: str, /) -> list[EventEmitter]:
        return self._listeners[event_name]

    @validate_arguments(event_name_validator)
    def add_listener(self, event_name: str, /, listener) -> EventEmitter:
        self._listeners[event_name].append(listener)
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
        try:
            deferred_emits = self._deferred_emits_var.get()
        except LookupError:
            # Initial call to emit, setup to catch and handle eventual
            # recursive calls
            deferred_emits = []
            token = self._deferred_emits_var.set(deferred_emits)
        else:
            # We've been recursively called as a result by a listener
            deferred_emits.append((event_name, args, kwargs))
            # TODO: Check to see if this is actually valid since we defer
            return bool(self._listeners[event_name])

        listeners = self._listeners[event_name]
        # We must store this first's call return value as we might
        # overwrite `listeners`
        ret = bool(listeners)
        while True:
            for listener in listeners:
                if asyncio.iscoroutinefunction(listener):
                    loop = asyncio.get_running_loop()
                    loop.create_task(listener(*args, **kwargs))
                else:
                    listener(*args, **kwargs)
            try:
                event_name, args, kwargs = deferred_emits.pop(0)
            except IndexError:
                # We've handled all deferred calls
                self._deferred_emits_var.reset(token)
                return ret
            else:
                listeners = self._listeners[event_name]


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
