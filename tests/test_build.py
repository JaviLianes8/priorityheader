import pytest

from priorityheader import PriorityError, build_priority, parse_priority


def test_build_omits_both_defaults() -> None:
    assert build_priority() == ""


def test_build_omits_the_default_urgency() -> None:
    assert build_priority(incremental=True) == "i"


def test_build_omits_a_false_incremental_flag() -> None:
    assert build_priority(urgency=1) == "u=1"


def test_build_renders_both_members() -> None:
    assert build_priority(urgency=0, incremental=True) == "u=0, i"


def test_build_renders_the_highest_urgency() -> None:
    assert build_priority(urgency=7) == "u=7"


def test_build_rejects_an_urgency_above_the_range() -> None:
    with pytest.raises(PriorityError):
        build_priority(urgency=8)


def test_build_rejects_an_urgency_below_the_range() -> None:
    with pytest.raises(PriorityError):
        build_priority(urgency=-1)


def test_build_rejects_a_boolean_urgency() -> None:
    with pytest.raises(TypeError):
        build_priority(urgency=True)


def test_build_rejects_a_non_integer_urgency() -> None:
    with pytest.raises(TypeError):
        build_priority(urgency="3")  # type: ignore[arg-type]


def test_build_rejects_a_non_boolean_incremental() -> None:
    with pytest.raises(TypeError):
        build_priority(incremental=1)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "urgency,incremental",
    [(3, False), (0, True), (7, False), (2, True), (5, False)],
)
def test_build_then_parse_round_trips(urgency: int, incremental: bool) -> None:
    rendered = build_priority(urgency=urgency, incremental=incremental)
    assert parse_priority(rendered) == (urgency, incremental)
