from typing import Any

import pytest

from app.modules.rules.engine import (
    ExpressionDepthError,
    ExpressionEvaluator,
    ExpressionTypeError,
    ExpressionValueError,
    RegexEvaluationError,
    UnknownOperatorError,
    json_truthy,
)


@pytest.fixture
def evaluator() -> ExpressionEvaluator:
    return ExpressionEvaluator()


def test_json_truthiness() -> None:
    assert json_truthy(True) is True
    assert json_truthy("hello") is True
    assert json_truthy([1]) is True
    assert json_truthy({"a": 1}) is True
    assert json_truthy(10) is True

    assert json_truthy(None) is False
    assert json_truthy(False) is False
    assert json_truthy(0) is False
    assert json_truthy(0.0) is False
    assert json_truthy("") is False
    assert json_truthy([]) is False
    assert json_truthy({}) is False


def test_primitive_and_array_literals(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate(42, {}) == 42
    assert evaluator.evaluate("string", {}) == "string"
    assert evaluator.evaluate(True, {}) is True
    assert evaluator.evaluate([1, 2, {"var": "x"}], {"x": 3}) == [1, 2, 3]
    assert evaluator.evaluate({}, {}) == {}


def test_malformed_ast_node(evaluator: ExpressionEvaluator) -> None:
    with pytest.raises(ExpressionValueError, match="exactly one operator key"):
        evaluator.evaluate({"eq": [1, 1], "gt": [2, 1]}, {})


def test_unknown_operator(evaluator: ExpressionEvaluator) -> None:
    with pytest.raises(UnknownOperatorError, match="Unknown or unregistered operator"):
        evaluator.evaluate({"unsupported_op": [1, 2]}, {})


def test_recursion_depth_limit(evaluator: ExpressionEvaluator) -> None:
    nested: dict[str, Any] = {"var": "x"}
    for _ in range(35):
        nested = {"+": [nested, 1]}

    with pytest.raises(ExpressionDepthError, match="depth exceeds limit"):
        evaluator.evaluate(nested, {"x": 1})


def test_var_operator(evaluator: ExpressionEvaluator) -> None:
    data: dict[str, Any] = {"user": {"profile": {"age": 30}, "items": ["a", "b"]}}
    assert evaluator.evaluate({"var": "user.profile.age"}, data) == 30
    assert evaluator.evaluate({"var": "user.items.1"}, data) == "b"
    assert evaluator.evaluate({"var": "user.missing"}, data) is None
    assert evaluator.evaluate({"var": ["user.missing", "default"]}, data) == "default"
    assert evaluator.evaluate({"var": ""}, data) == data
    assert evaluator.evaluate({"var": "user.profile.age.invalid"}, data) is None
    assert evaluator.evaluate({"var": "user.items.invalid_idx"}, data) is None
    assert evaluator.evaluate({"var": "user.items.10"}, data) is None


def test_has_operator(evaluator: ExpressionEvaluator) -> None:
    data: dict[str, Any] = {"patient": {"id": "P123"}}
    assert evaluator.evaluate({"has": "patient.id"}, data) is True
    assert evaluator.evaluate({"has": "patient.ssn"}, data) is False

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"has": []}, data)


def test_eq_operator(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"eq": [10, 10]}, {}) is True
    assert evaluator.evaluate({"eq": ["a", "b"]}, {}) is False

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"eq": [1]}, {})


def test_gt_operator(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"gt": [10, 5]}, {}) is True
    assert evaluator.evaluate({"gt": [5, 10]}, {}) is False

    with pytest.raises(ExpressionTypeError):
        evaluator.evaluate({"gt": ["10", 5]}, {})

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"gt": [5]}, {})


def test_and_short_circuit(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"and": [False, {"gt": [10, 0]}]}, {}) is False
    assert evaluator.evaluate({"and": [10, "truthy"]}, {}) == "truthy"
    assert evaluator.evaluate({"and": []}, {}) is True


def test_or_short_circuit(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"or": ["first_truthy", {"gt": [10, 0]}]}, {}) == "first_truthy"
    assert evaluator.evaluate({"or": [False, 0, "fallback"]}, {}) == "fallback"
    assert evaluator.evaluate({"or": []}, {}) is False


def test_if_operator(evaluator: ExpressionEvaluator) -> None:
    expr: dict[str, Any] = {
        "if": [{"gt": [{"var": "score"}, 90]}, "A", {"gt": [{"var": "score"}, 80]}, "B", "C"]
    }
    assert evaluator.evaluate(expr, {"score": 95}) == "A"
    assert evaluator.evaluate(expr, {"score": 85}) == "B"
    assert evaluator.evaluate(expr, {"score": 70}) == "C"

    expr_even: dict[str, Any] = {"if": [True, "Yes"]}
    assert evaluator.evaluate(expr_even, {}) == "Yes"

    expr_even_falsy: dict[str, Any] = {"if": [False, "Yes"]}
    assert evaluator.evaluate(expr_even_falsy, {}) is None

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"if": [True]}, {})


def test_in_operator(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"in": ["cat", "catalog"]}, {}) is True
    assert evaluator.evaluate({"in": [2, [1, 2, 3]]}, {}) is True
    assert (
        evaluator.evaluate({"in": ["key", {"var": "lookup"}]}, {"lookup": {"key": "val"}}) is True
    )
    assert evaluator.evaluate({"in": [5, None]}, {}) is False

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"in": [1]}, {})


def test_count_operator(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"count": [[1, 2, 3]]}, {}) == 3
    assert evaluator.evaluate({"count": "hello"}, {}) == 5

    with pytest.raises(ExpressionTypeError):
        evaluator.evaluate({"count": 123}, {})

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"count": []}, {})


def test_all_any_map_filter_operators(evaluator: ExpressionEvaluator) -> None:
    data: dict[str, Any] = {"lines": [{"amount": 100}, {"amount": 200}]}

    assert (
        evaluator.evaluate({"all": [{"var": "lines"}, {"gt": [{"var": "amount"}, 50]}]}, data)
        is True
    )
    assert evaluator.evaluate({"all": [[], {"gt": [{"var": "amount"}, 50]}]}, data) is True

    assert (
        evaluator.evaluate({"any": [{"var": "lines"}, {"gt": [{"var": "amount"}, 150]}]}, data)
        is True
    )
    assert (
        evaluator.evaluate({"any": [{"var": "lines"}, {"gt": [{"var": "amount"}, 500]}]}, data)
        is False
    )

    mapped = evaluator.evaluate({"map": [{"var": "lines"}, {"var": "amount"}]}, data)
    assert mapped == [100, 200]

    filtered = evaluator.evaluate(
        {"filter": [{"var": "lines"}, {"gt": [{"var": "amount"}, 150]}]}, data
    )
    assert filtered == [{"amount": 200}]


def test_collection_operator_errors(evaluator: ExpressionEvaluator) -> None:
    with pytest.raises(ExpressionTypeError):
        evaluator.evaluate({"all": ["not_a_list", True]}, {})

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"map": [[1, 2]]}, {})


def test_arithmetic_operators(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"+": [10, 20, 30]}, {}) == 60
    assert evaluator.evaluate({"-": [100, 30]}, {}) == 70
    assert evaluator.evaluate({"-": [5]}, {}) == -5
    assert evaluator.evaluate({"*": [2, 3, 4]}, {}) == 24
    assert evaluator.evaluate({"*": [5]}, {}) == 5
    assert evaluator.evaluate({"/": [10, 2]}, {}) == 5.0


def test_arithmetic_operator_errors(evaluator: ExpressionEvaluator) -> None:
    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"+": []}, {})

    with pytest.raises(ExpressionTypeError):
        evaluator.evaluate({"+": [10, "invalid"]}, {})

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"-": [1, 2, 3]}, {})

    with pytest.raises(ExpressionValueError):
        evaluator.evaluate({"/": [10, 0]}, {})


def test_regex_match(evaluator: ExpressionEvaluator) -> None:
    assert evaluator.evaluate({"regex_match": ["D1234", "^D[0-9]{4}$"]}, {}) is True
    assert evaluator.evaluate({"regex_match": ["INVALID", "^D[0-9]{4}$"]}, {}) is False


def test_regex_errors_and_limits(evaluator: ExpressionEvaluator) -> None:
    with pytest.raises(RegexEvaluationError, match="Invalid regex pattern"):
        evaluator.evaluate({"regex_match": ["test", "[unclosed-group"]}, {})

    long_pattern = "a" * 201
    with pytest.raises(RegexEvaluationError, match="exceeds maximum length"):
        evaluator.evaluate({"regex_match": ["test", long_pattern]}, {})

    with pytest.raises(ExpressionTypeError):
        evaluator.evaluate({"regex_match": [123, "^[0-9]+$"]}, {})
