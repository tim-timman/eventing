"""Eventing package for Python.

A pythonic event emitter inspired by Node.js'
EventEmitter and Python's logging libraries.
"""

from __future__ import annotations

__version__ = "0.1.0"


class Manager:
    def __init__(self, root_node):
        self.root = root_node
        self.emitter_dict = {}

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

    def __init__(self, name: str):
        self.name = name


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
