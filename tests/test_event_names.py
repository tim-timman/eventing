from collections import namedtuple
import functools

import pytest

import eventing


def a_listener():
    pass


FuncBindSign = namedtuple("FuncBindSign", ["func_name", "params_to_bind"])

functions_using_event_name_with_args_signatures = [
    FuncBindSign("listener_count", {}),
    FuncBindSign("listeners", {}),
    FuncBindSign("add_listener", {"listener": a_listener}),
    FuncBindSign("remove_listener", {"listener": a_listener}),
]


def get_function_bound_for_call_with_event_name_only(
    ee: eventing.EventEmitter, func_bind_sign: FuncBindSign
):
    func = getattr(ee, func_bind_sign.func_name)
    return functools.partial(func, **func_bind_sign.params_to_bind)


@pytest.fixture(params=functions_using_event_name_with_args_signatures)
def func_wrapped_for_event_name(request):
    ee = eventing.get_emitter()
    return get_function_bound_for_call_with_event_name_only(ee, request.param)


def test_event_names_may_only_be_strings(func_wrapped_for_event_name):
    with pytest.raises(TypeError):
        func_wrapped_for_event_name(False)


def test_event_name_may_not_be_empty(func_wrapped_for_event_name):
    with pytest.raises(ValueError, match="must not be empty"):
        func_wrapped_for_event_name("")
