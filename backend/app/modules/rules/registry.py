import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


class ArityMismatchError(Exception):
    """Raised when a rule configuration passes an invalid number of arguments to an operator."""

    pass


class UnknownOperatorError(Exception):
    """Raised when a rule references an unregistered operator."""

    pass


@dataclass(frozen=True)
class OperatorSpec:
    name: str
    fn: Callable[..., Any]
    min_arity: int
    max_arity: int | None  # None if the operator accepts *args


class OperatorRegistry:
    _operators: dict[str, OperatorSpec] = {}

    @classmethod
    def register(cls, name: str | None = None) -> Callable[..., Any]:
        """Decorator to register a domain operator and calculate its arity limits."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            op_name = (name or fn.__name__).strip().lower()
            sig = inspect.signature(fn)

            min_args = 0
            max_args = 0
            is_variadic = False

            for param in sig.parameters.values():
                if param.kind == inspect.Parameter.VAR_POSITIONAL:
                    is_variadic = True
                elif param.kind in (
                    inspect.Parameter.POSITIONAL_ONLY,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                ):
                    max_args += 1
                    if param.default == inspect.Parameter.empty:
                        min_args += 1

            cls._operators[op_name] = OperatorSpec(
                name=op_name,
                fn=fn,
                min_arity=min_args,
                max_arity=None if is_variadic else max_args,
            )
            return fn

        return decorator

    @classmethod
    def get(cls, name: str) -> OperatorSpec:
        op_name = name.strip().lower()
        if op_name not in cls._operators:
            raise UnknownOperatorError(f"Operator '{name}' is not registered.")
        return cls._operators[op_name]

    @classmethod
    def validate_call(cls, name: str, provided_arg_count: int) -> None:
        """Validates arity at load/startup time before claim execution."""
        spec = cls.get(name)

        if provided_arg_count < spec.min_arity:
            raise ArityMismatchError(
                f"Operator '{spec.name}' requires at least {spec.min_arity} argument(s), "
                f"but rule passed {provided_arg_count}."
            )

        if spec.max_arity is not None and provided_arg_count > spec.max_arity:
            raise ArityMismatchError(
                f"Operator '{spec.name}' accepts at most {spec.max_arity} argument(s), "
                f"but rule passed {provided_arg_count}."
            )
