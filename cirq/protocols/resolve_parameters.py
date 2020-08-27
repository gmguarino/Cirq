# Copyright 2018 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import AbstractSet, Any, TypeVar, TYPE_CHECKING
from typing_extensions import Protocol
import sympy

from cirq import study
from cirq._doc import document

if TYPE_CHECKING:
    import cirq

TDefault = TypeVar('TDefault')


class SupportsParameterization(Protocol):
    """An object that can be parameterized by Symbols and resolved
    via a ParamResolver"""

    @document
    def _is_parameterized_(self: Any) -> bool:
        """Whether the object is parameterized by any Symbols that require
        resolution. Returns True if the object has any unresolved Symbols
        and False otherwise."""

    @document
    def _parameter_names_(self: Any) -> AbstractSet[str]:
        """Returns a collection of string names of parameters that require
        resolution. The collection is empty iff _is_parameterized_ is False.
        """

    @document
    def _parameter_symbols_(self, Any) -> AbstractSet[sympy.Symbol]:
        """Returns a collection of sympy Symbols of parameters that require
        resolution. The collection is empty iff _is_parameterized_ is False.
        """

    @document
    def _resolve_parameters_(self: Any, param_resolver: 'cirq.ParamResolver'):
        """Resolve the parameters in the effect."""


def is_parameterized(val: Any) -> bool:
    """Returns whether the object is parameterized with any Symbols.

    A value is parameterized when it has an `_is_parameterized_` method and
    that method returns a truthy value, or if the value is an instance of
    sympy.Basic.

    Returns:
        True if the gate has any unresolved Symbols
        and False otherwise. If no implementation of the magic
        method above exists or if that method returns NotImplemented,
        this will default to False.
    """
    if isinstance(val, sympy.Basic):
        return True
    if isinstance(val, (list, tuple)):
        return any(is_parameterized(e) for e in val)

    getter = getattr(val, '_is_parameterized_', None)
    result = NotImplemented if getter is None else getter()

    if result is not NotImplemented:
        return result
    else:
        return False


def parameter_names(val: Any, *, check_symbols: bool = True) -> AbstractSet[str]:
    """Returns parameter names for this object.

    Args:
        val: Object for which to find the parameter names.
        check_symbols: If true, fall back to calling parameter_symbols.

    Returns:
        A set of parameter names if the object is parameterized. It the object
        does not implement the _parameter_names_ magic method or that method
        returns NotImplemented, returns an empty set.
    """
    if isinstance(val, sympy.Basic):
        return {symbol.name for symbol in val.free_symbols}
    if isinstance(val, (list, tuple)):
        return {name for e in val for name in parameter_names(e)}

    getter = getattr(val, '_parameter_names_', None)
    result = NotImplemented if getter is None else getter()
    if result is not NotImplemented:
        return result

    if check_symbols:
        symbols = parameter_symbols(val, check_names=False)
        if symbols is not NotImplemented:
            return {symbol.name for symbol in symbols}

    return set()


def parameter_symbols(val: Any, *, check_names: bool = True) -> AbstractSet[sympy.Symbol]:
    """Returns parameter symbols for this object.

    Args:
        val: Object for which to find the parameter symbols.
        check_names: If true, fall back to calling parameter_names.

    Returns:
        A set of parameter symbols if the object is parameterized. It the object
        does not implement the _parameter_symbols_ magic method or that method
        returns NotImplemented, returns an empty set.
    """
    if isinstance(val, sympy.Basic):
        return val.free_symbols
    if isinstance(val, (list, tuple)):
        return {symbol for e in val for symbol in parameter_symbols(e)}

    getter = getattr(val, '_parameter_symbols_', None)
    result = NotImplemented if getter is None else getter()
    if result is not NotImplemented:
        return result

    if check_names:
        names = parameter_names(val, check_symbols=False)
        if names is not NotImplemented:
            return {sympy.Symbol(name) for name in names}

    return set()


def resolve_parameters(
        val: Any,
        param_resolver: 'cirq.ParamResolverOrSimilarType') -> Any:
    """Resolves symbol parameters in the effect using the param resolver.

    This function will use the `_resolve_parameters_` magic method
    of `val` to resolve any Symbols with concrete values from the given
    parameter resolver.

    Args:
        val: The object to resolve (e.g. the gate, operation, etc)
        param_resolver: the object to use for resolving all symbols

    Returns:
        a gate or operation of the same type, but with all Symbols
        replaced with floats according to the given ParamResolver.
        If `val` has no `_resolve_parameters_` method or if it returns
        NotImplemented, `val` itself is returned.
    """
    if not param_resolver:
        return val

    # Ensure its a dictionary wrapped in a ParamResolver.
    param_resolver = study.ParamResolver(param_resolver)
    if isinstance(val, sympy.Basic):
        return param_resolver.value_of(val)
    if isinstance(val, (list, tuple)):
        return type(val)(resolve_parameters(e, param_resolver) for e in val)

    getter = getattr(val, '_resolve_parameters_', None)
    result = NotImplemented if getter is None else getter(param_resolver)

    if result is not NotImplemented:
        return result
    else:
        return val
