import re
from collections.abc import Callable
from typing import Any

JSONValue = None | bool | int | float | str | list[Any] | dict[str, Any]


class ExpressionError(Exception):
    """Base exception for expression parsing and execution failures."""


class UnknownOperatorError(ExpressionError):
    """Raised when an expression contains an operator not in the registry."""


class ExpressionDepthError(ExpressionError):
    """Raised when an expression tree exceeds the maximum permitted depth."""


class ExpressionTypeError(ExpressionError):
    """Raised when an operation receives an invalid data type."""


class ExpressionValueError(ExpressionError):
    """Raised when an expression operation receives invalid arguments."""


class RegexEvaluationError(ExpressionError):
    """Raised when regex evaluation times out or encounters invalid patterns."""


def json_truthy(val: Any) -> bool:
    """Evaluates JSON-compatible values according to standard JSONLogic truthiness."""
    if val is None or val is False:
        return False
    if isinstance(val, (int, float)) and val == 0:
        return False
    if isinstance(val, (str, list, dict)) and len(val) == 0:
        return False
    return True


class ExpressionEvaluator:
    """Safe, restricted interpreter for JSONLogic-derived expression ASTs."""

    MAX_DEPTH = 30
    MAX_COLLECTION_SIZE = 10000
    MAX_REGEX_PATTERN_LENGTH = 200

    def __init__(self, registry: dict[str, Callable[[list[Any], Any, int], Any]] | None = None):
        self.registry = registry if registry is not None else self._build_default_registry()

    def _build_default_registry(self) -> dict[str, Callable[[list[Any], Any, int], Any]]:
        return {
            "var": self._op_var,
            "has": self._op_has,
            "eq": self._op_eq,
            "gt": self._op_gt,
            "and": self._op_and,
            "or": self._op_or,
            "if": self._op_if,
            "in": self._op_in,
            "count": self._op_count,
            "all": self._op_all,
            "any": self._op_any,
            "map": self._op_map,
            "filter": self._op_filter,
            "+": self._op_add,
            "-": self._op_sub,
            "*": self._op_mul,
            "/": self._op_div,
            "regex_match": self._op_regex_match,
        }

    def evaluate(self, expr: JSONValue, data: Any, depth: int = 0) -> Any:
        """Recursively evaluates an AST node against a context data dictionary or scalar."""
        if depth > self.MAX_DEPTH:
            raise ExpressionDepthError(f"Expression tree depth exceeds limit of {self.MAX_DEPTH}")

        if not isinstance(expr, dict):
            if isinstance(expr, list):
                return [self.evaluate(elem, data, depth + 1) for elem in expr]
            return expr

        if not expr:
            return {}

        if len(expr) != 1:
            raise ExpressionValueError("Expression node must contain exactly one operator key")

        op = next(iter(expr))
        if op not in self.registry:
            raise UnknownOperatorError(f"Unknown or unregistered operator: '{op}'")

        raw_args = expr[op]
        args = raw_args if isinstance(raw_args, list) else [raw_args]

        return self.registry[op](args, data, depth)

    def _resolve_var(self, path: Any, data: Any) -> Any:
        if path == "" or path is None:
            return data

        parts = str(path).split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                if part in current:
                    current = current[part]
                elif part.isdigit() and int(part) in current:
                    current = current[int(part)]
                else:
                    return None
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if idx < 0 or idx >= len(current):
                        return None
                    current = current[idx]
                except ValueError:
                    return None
            else:
                return None
        return current

    def _op_var(self, args: list[Any], data: Any, depth: int) -> Any:
        path = self.evaluate(args[0], data, depth + 1) if args else ""
        default = self.evaluate(args[1], data, depth + 1) if len(args) > 1 else None
        resolved = self._resolve_var(path, data)
        return resolved if resolved is not None else default

    def _op_has(self, args: list[Any], data: Any, depth: int) -> bool:
        if not args:
            raise ExpressionValueError("'has' operator requires at least 1 path argument")
        path = self.evaluate(args[0], data, depth + 1)
        return self._resolve_var(path, data) is not None

    def _op_eq(self, args: list[Any], data: Any, depth: int) -> bool:
        if len(args) != 2:
            raise ExpressionValueError("'eq' operator requires exactly 2 arguments")
        val1 = self.evaluate(args[0], data, depth + 1)
        val2 = self.evaluate(args[1], data, depth + 1)
        return bool(val1 == val2)

    def _op_gt(self, args: list[Any], data: Any, depth: int) -> bool:
        if len(args) != 2:
            raise ExpressionValueError("'gt' operator requires exactly 2 arguments")
        val1 = self.evaluate(args[0], data, depth + 1)
        val2 = self.evaluate(args[1], data, depth + 1)

        if (
            not isinstance(val1, (int, float))
            or not isinstance(val2, (int, float))
            or isinstance(val1, bool)
            or isinstance(val2, bool)
        ):
            raise ExpressionTypeError("'gt' operator requires numeric operands")
        return val1 > val2

    def _op_and(self, args: list[Any], data: Any, depth: int) -> Any:
        if not args:
            return True
        last_val = True
        for arg in args:
            val = self.evaluate(arg, data, depth + 1)
            if not json_truthy(val):
                return val
            last_val = val
        return last_val

    def _op_or(self, args: list[Any], data: Any, depth: int) -> Any:
        if not args:
            return False
        last_val = False
        for arg in args:
            val = self.evaluate(arg, data, depth + 1)
            if json_truthy(val):
                return val
            last_val = val
        return last_val

    def _op_if(self, args: list[Any], data: Any, depth: int) -> Any:
        if len(args) < 2:
            raise ExpressionValueError("'if' operator requires at least 2 arguments")

        idx = 0
        while idx < len(args):
            if idx == len(args) - 1:
                return self.evaluate(args[idx], data, depth + 1)

            condition = self.evaluate(args[idx], data, depth + 1)
            if json_truthy(condition):
                return self.evaluate(args[idx + 1], data, depth + 1)
            idx += 2

        return None

    def _op_in(self, args: list[Any], data: Any, depth: int) -> bool:
        if len(args) != 2:
            raise ExpressionValueError("'in' operator requires exactly 2 arguments")

        item = self.evaluate(args[0], data, depth + 1)
        container = self.evaluate(args[1], data, depth + 1)

        if isinstance(container, str):
            if not isinstance(item, str):
                return False
            return item in container
        if isinstance(container, set):
            try:
                return item in container
            except TypeError:
                return False
        if isinstance(container, list):
            return item in container
        if isinstance(container, dict):
            return str(item) in container

        return False

    def _op_count(self, args: list[Any], data: Any, depth: int) -> int:
        if len(args) != 1:
            raise ExpressionValueError("'count' operator requires exactly 1 argument")

        coll = self.evaluate(args[0], data, depth + 1)
        if isinstance(coll, (list, dict, str, set)):
            return len(coll)
        raise ExpressionTypeError("'count' operator requires a collection or string target")

    def _validate_collection(self, coll: Any, op_name: str) -> list[Any]:
        if not isinstance(coll, list):
            raise ExpressionTypeError(f"First argument of '{op_name}' must evaluate to a list")
        if len(coll) > self.MAX_COLLECTION_SIZE:
            raise ExpressionValueError(
                f"Collection size exceeds limit of {self.MAX_COLLECTION_SIZE}"
            )
        return coll

    def _op_all(self, args: list[Any], data: Any, depth: int) -> bool:
        if len(args) != 2:
            raise ExpressionValueError(
                "'all' operator requires 2 arguments: [collection, scoped_expression]"
            )

        coll = self._validate_collection(self.evaluate(args[0], data, depth + 1), "all")
        if not coll:
            return True

        sub_expr = args[1]
        for elem in coll:
            res = self.evaluate(sub_expr, elem, depth + 1)
            if not json_truthy(res):
                return False
        return True

    def _op_any(self, args: list[Any], data: Any, depth: int) -> bool:
        if len(args) != 2:
            raise ExpressionValueError(
                "'any' operator requires 2 arguments: [collection, scoped_expression]"
            )

        coll = self._validate_collection(self.evaluate(args[0], data, depth + 1), "any")
        sub_expr = args[1]
        for elem in coll:
            res = self.evaluate(sub_expr, elem, depth + 1)
            if json_truthy(res):
                return True
        return False

    def _op_map(self, args: list[Any], data: Any, depth: int) -> list[Any]:
        if len(args) != 2:
            raise ExpressionValueError(
                "'map' operator requires 2 arguments: [collection, mapped_expression]"
            )

        coll = self._validate_collection(self.evaluate(args[0], data, depth + 1), "map")
        sub_expr = args[1]
        return [self.evaluate(sub_expr, elem, depth + 1) for elem in coll]

    def _op_filter(self, args: list[Any], data: Any, depth: int) -> list[Any]:
        if len(args) != 2:
            raise ExpressionValueError(
                "'filter' operator requires 2 arguments: [collection, predicate_expression]"
            )

        coll = self._validate_collection(self.evaluate(args[0], data, depth + 1), "filter")
        sub_expr = args[1]
        return [elem for elem in coll if json_truthy(self.evaluate(sub_expr, elem, depth + 1))]

    def _op_add(self, args: list[Any], data: Any, depth: int) -> int | float:
        if not args:
            raise ExpressionValueError("'+' operator requires at least 1 argument")
        total: int | float = 0
        for arg in args:
            val = self.evaluate(arg, data, depth + 1)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ExpressionTypeError("'+' operator requires numeric operands")
            total += val
        return total

    def _op_sub(self, args: list[Any], data: Any, depth: int) -> int | float:
        if not args or len(args) > 2:
            raise ExpressionValueError("'-' operator requires 1 or 2 arguments")

        vals = [self.evaluate(arg, data, depth + 1) for arg in args]
        for v in vals:
            if not isinstance(v, (int, float)) or isinstance(v, bool):
                raise ExpressionTypeError("'-' operator requires numeric operands")

        if len(vals) == 1:
            val: int | float = vals[0]
            return -val
        val1: int | float = vals[0]
        val2: int | float = vals[1]
        return val1 - val2

    def _op_mul(self, args: list[Any], data: Any, depth: int) -> int | float:
        if not args:
            raise ExpressionValueError("'*' operator requires at least 1 argument")
        total: int | float = 1
        for arg in args:
            val = self.evaluate(arg, data, depth + 1)
            if not isinstance(val, (int, float)) or isinstance(val, bool):
                raise ExpressionTypeError("'*' operator requires numeric operands")
            total *= val
        return total

    def _op_div(self, args: list[Any], data: Any, depth: int) -> float:
        if len(args) != 2:
            raise ExpressionValueError("'/' operator requires exactly 2 arguments")

        val1 = self.evaluate(args[0], data, depth + 1)
        val2 = self.evaluate(args[1], data, depth + 1)

        if (
            not isinstance(val1, (int, float))
            or not isinstance(val2, (int, float))
            or isinstance(val1, bool)
            or isinstance(val2, bool)
        ):
            raise ExpressionTypeError("'/' operator requires numeric operands")

        if val2 == 0:
            raise ExpressionValueError("Division by zero")

        return val1 / val2

    def _op_regex_match(self, args: list[Any], data: Any, depth: int) -> bool:
        if len(args) != 2:
            raise ExpressionValueError("'regex_match' requires 2 arguments: [string, pattern]")

        target = self.evaluate(args[0], data, depth + 1)
        pattern = self.evaluate(args[1], data, depth + 1)

        if not isinstance(target, str) or not isinstance(pattern, str):
            raise ExpressionTypeError("'regex_match' requires string operands")

        if len(pattern) > self.MAX_REGEX_PATTERN_LENGTH:
            raise RegexEvaluationError(
                f"Regex pattern exceeds maximum length of {self.MAX_REGEX_PATTERN_LENGTH}"
            )

        try:
            compiled = re.compile(pattern)
            return bool(compiled.search(target))
        except re.error as e:
            raise RegexEvaluationError(f"Invalid regex pattern: {e}") from e
