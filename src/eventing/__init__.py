"""Eventing package for Python.

A pythonic event emitter inspired by Node.js'
EventEmitter and Python's logging libraries.
"""

from __future__ import annotations

__version__ = "0.2.0"

import asyncio
from asyncio import AbstractEventLoop
from collections import defaultdict
from collections import deque
import contextlib
from contextvars import ContextVar
import dis
import functools
from functools import wraps
import inspect
import itertools
import operator
from types import FrameType
from typing import Iterator, Sequence, TypeVar
import warnings

from .exceptions import MissingClassMethodHandler
from .exceptions import NoEventLoopError
from .exceptions import NotAClassError
from .validation import event_name_validator
from .validation import validate_arguments


class PlaceHolder:
    def __init__(self, emitter):
        self.parent: EventEmitter
        self.children = {emitter}

    def add_child(self, emitter):
        self.children.add(emitter)


class Manager:
    def __init__(self, root_node: EventEmitter):
        self.root = root_node
        self.emitter_dict: dict[str, EventEmitter | PlaceHolder] = {}

    def get_emitter(self, name: str) -> EventEmitter:
        if not isinstance(name, str):
            raise TypeError("An emitter name must be a string")
        if name in self.emitter_dict:
            emitter = self.emitter_dict[name]
            if isinstance(emitter, PlaceHolder):
                place_holder, emitter = emitter, EventEmitter(name)
                self.emitter_dict[name] = emitter
                self._fixup_children(place_holder, emitter)
                self._fixup_parents(emitter)
        else:
            emitter = EventEmitter(name)
            self.emitter_dict[name] = emitter
            self._fixup_parents(emitter)
        return emitter

    def _fixup_children(self, place_holder: PlaceHolder, emitter: EventEmitter) -> None:
        name = emitter.name
        for child in place_holder.children:
            child_already_has_parent_thats_child_of_emitter = (
                child._parent.name.startswith(name)
            )
            if not child_already_has_parent_thats_child_of_emitter:
                child._parent = emitter

    def _fixup_parents(self, emitter: EventEmitter) -> None:
        name = emitter.name
        idx = name.rfind(".")
        real_parent = None
        while (idx > 0) and real_parent is None:
            parent_name = name[:idx]
            if parent_name not in self.emitter_dict:
                self.emitter_dict[parent_name] = PlaceHolder(emitter)
            else:
                potential_parent = self.emitter_dict[parent_name]
                if isinstance(potential_parent, EventEmitter):
                    real_parent = potential_parent
                else:
                    assert isinstance(potential_parent, PlaceHolder)
                    potential_parent.add_child(emitter)
            idx = parent_name.rfind(".")
        if real_parent is None:
            real_parent = self.root
        emitter._parent = real_parent


T = TypeVar("T")
CLASS_DUNDER = "__eventing_class_magic__"


def handle_methods(cls: type[T]) -> type[T]:
    members = [
        (name, func)
        for name, func in vars(cls).items()
        if not name.startswith("__") and inspect.isroutine(func)
    ]

    handled_listeners = False
    instance_listeners = []
    listener_metadata: deque[tuple[str, str]]
    for listener_name, func in members:
        if isinstance(func, (staticmethod, classmethod)) and hasattr(
            func.__func__, CLASS_DUNDER
        ):
            listener_metadata = getattr(func.__func__, CLASS_DUNDER)
            listener = getattr(cls, listener_name)
            emitter_name, event_name = listener_metadata.popleft()
            # @Performance
            get_emitter(emitter_name).add_listener(event_name, listener)
            if not listener_metadata:
                delattr(func.__func__, CLASS_DUNDER)
            handled_listeners = True

        elif hasattr(func, CLASS_DUNDER):
            listener_metadata = getattr(func, CLASS_DUNDER)
            emitter_name, event_name = listener_metadata.popleft()
            instance_listeners.append((emitter_name, event_name, listener_name))
            if not listener_metadata:
                delattr(func, CLASS_DUNDER)
            handled_listeners = True

    if instance_listeners:
        setattr(
            cls,
            "__init__",
            _add_instance_listeners(cls, instance_listeners),
        )

    if not handled_listeners:
        warnings.warn(
            "@ee.handle_methods wrapped class without any listeners to setup.\n"
            "    Hint: did you forget `@ee.on(..., method=True)`"
        )

    return cls


def __dummy_init__(self, *args, **kwargs) -> None:
    super(self.__class__.__mro__[0], self).__init__(*args, **kwargs)


def _add_instance_listeners(
    cls: type[T], instance_listeners: Sequence[tuple[str, str, str]]
):
    __init__ = vars(cls).get("__init__", __dummy_init__)

    @wraps(__init__)
    def wrapper(self: T, *args, **kwargs) -> None:
        __init__(self, *args, **kwargs)
        for emitter_name, event_name, method_name in instance_listeners:
            instance_listener = getattr(self, method_name)
            get_emitter(emitter_name).add_listener(event_name, instance_listener)

    return wrapper


class EventEmitter:
    manager: Manager
    root: RootEmitter
    handle_methods = staticmethod(handle_methods)
    _deferred_emits_var: ContextVar[deque] = ContextVar("deferred_emits")

    def __init__(self, name: str):
        self.name = name
        self._listeners: defaultdict[str, list] = defaultdict(list)

        self._loop: AbstractEventLoop | None = None
        self._parent: EventEmitter | None = None

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
        listeners = self._listeners[event_name].copy()
        # We must store this first's call return value as we might
        # overwrite `listeners`
        return_value = bool(listeners)

        with self._defer_emits(event_name, args, kwargs) as deferred_emits:
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
            token = None
        except LookupError:
            # Initial call to emit, setup to catch and handle eventual
            # recursive calls
            deferred_emits = deque(((event_name, args, kwargs),))
            token = self._deferred_emits_var.set(deferred_emits)

            def defer_generator():
                try:
                    while True:
                        yield deferred_emits.popleft()
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
            if token is not None:
                self._deferred_emits_var.reset(token)

    def _get_loop(self):
        ee = self
        while (loop := ee._loop) is None:
            ee = ee._parent
            if ee is None:
                raise NoEventLoopError(
                    "No event loop configured.\n    Hint: use "
                    "`eventing.set_event_loop(asyncio.get_running_loop())` "
                    "at top of your asyncio entrypoint."
                )
        return loop

    def _emit(self, listener, args, kwargs):
        if asyncio.iscoroutinefunction(listener):
            loop = self._get_loop()
            try:
                running_loop = asyncio.get_running_loop()
            except RuntimeError:
                running_loop = None
            coro = listener(*args, **kwargs)
            if running_loop is None or running_loop != loop:
                asyncio.run_coroutine_threadsafe(coro, loop)
            else:
                loop.create_task(coro)
        else:
            listener(*args, **kwargs)

    def _check_if_class_has_decorator(
        self,
        class_creation_frame: FrameType,
        class_decorator_instructions: deque[dis.Instruction],
        decorator_func,
    ) -> None:
        tos = None
        f_locals = class_creation_frame.f_locals
        f_globals = class_creation_frame.f_globals
        for instr in class_decorator_instructions:
            obj = None
            # TODO: this is not exhaustive
            if instr.opname in ["LOAD_NAME", "LOAD_DEREF", "LOAD_GLOBAL"]:
                try:
                    obj = f_locals[instr.argval]
                except KeyError:
                    obj = f_globals[instr.argval]
            elif instr.opname == "LOAD_ATTR":
                obj = getattr(tos, instr.argval)

            if obj is not None:
                if obj == decorator_func:
                    break
                tos = obj

        else:
            raise MissingClassMethodHandler(
                "`method=True` but class not decorated with `@ee.handle_methods`"
            )

    def _check_if_method_and_class_has_decorator(
        self, decorator_frame: FrameType, decorator_func
    ) -> None:
        class_frame = decorator_frame.f_back
        if class_frame is None:
            raise NotAClassError

        class_creation_frame = class_frame.f_back
        if class_creation_frame is None:
            # Then we can't possibly be in a class because the stack isn't deep enough
            raise NotAClassError
        class_code = class_frame.f_code

        op = functools.partial(operator.is_not, class_code)
        # Get all previously run instructions up to where the class code was executed
        instructions = deque(
            itertools.takewhile(op, dis.get_instructions(class_creation_frame.f_code))
        )

        class_decorator_instructions: deque[dis.Instruction] = deque()
        part_of_class = False
        try:
            # iterate backwards
            while instr := instructions.pop():
                if not part_of_class:
                    if instr.opname == "LOAD_BUILD_CLASS":
                        part_of_class = True
                else:
                    if instr.opname.startswith("STORE_"):
                        break
                    else:
                        # put the back in normal order
                        class_decorator_instructions.appendleft(instr)
        except IndexError:
            if not part_of_class:
                raise NotAClassError from None

        self._check_if_class_has_decorator(
            class_creation_frame, class_decorator_instructions, decorator_func
        )

    @validate_arguments(event_name_validator)
    def on(self, event_name: str, /, *, method: bool = False):
        def inner(listener):
            if not method:
                self._on(event_name, listener)
            else:
                frame = inspect.currentframe()
                try:
                    self._check_if_method_and_class_has_decorator(
                        frame, self.handle_methods
                    )
                    if hasattr(listener, CLASS_DUNDER):
                        getattr(listener, CLASS_DUNDER).append((self.name, event_name))
                    else:
                        setattr(
                            listener, CLASS_DUNDER, deque(((self.name, event_name),))
                        )
                except NotAClassError:
                    raise ValueError(
                        "`method=True` may only be used on methods of a class"
                    ) from None
                finally:
                    del frame

            return listener

        return inner

    def _on(self, event_name: str, /, listener):
        self._listeners[event_name].append(listener)

    def set_event_loop(self, loop: AbstractEventLoop) -> None:
        self._loop = loop

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.name}>"


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


def set_event_loop(loop: AbstractEventLoop) -> None:
    root.set_event_loop(loop)
