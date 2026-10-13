import pytest

from priorityheader import Priority, PriorityError, parse_params, parse_priority


@pytest.mark.parametrize(
    "header,offset",
    [
        ("u=1,", 4),
        ("u=1 i", 4),
        ("u=1, i=?2", 8),
        ("U=1", 0),
        ("u=1, @x", 5),
        ('u=1, x="\u00e9"', 8),
        ('x="abc', 6),
        ("x=(1 2", 6),
        ("x=:%%:", 3),
        ("\tu=1", 0),
    ],
)
def test_strict_parse_reports_the_offset(header: str, offset: int) -> None:
    with pytest.raises(PriorityError) as caught:
        parse_priority(header, strict=True)
    assert caught.value.offset == offset
    assert f"offset {offset}" in str(caught.value)


def test_strict_parse_still_ignores_out_of_range_and_wrong_types() -> None:
    # RFC 9218 section 4: these are ignored once the Dictionary parses.
    assert parse_priority("u=9, i=3", strict=True) == Priority(3, False)


def test_strict_parse_accepts_an_empty_field() -> None:
    assert parse_priority("", strict=True) == Priority(3, False)
    assert parse_priority("   ", strict=True) == Priority(3, False)


def test_strict_parse_of_params_raises_too() -> None:
    with pytest.raises(PriorityError):
        parse_params("u=1,", strict=True)


def test_strict_offsets_count_in_the_joined_lines() -> None:
    with pytest.raises(PriorityError) as caught:
        parse_priority(["u=1", "i=?"], strict=True)
    assert caught.value.offset == len("u=1, i=?")


def test_priority_error_is_a_value_error() -> None:
    assert issubclass(PriorityError, ValueError)
    assert PriorityError("x").offset is None
