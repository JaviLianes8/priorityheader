import pytest

from priorityheader import Priority, parse_priority


def test_parse_reads_urgency_and_incremental() -> None:
    assert parse_priority("u=1, i") == Priority(1, True)


def test_parse_reads_an_explicit_boolean_true() -> None:
    assert parse_priority("u=5, i=?1") == Priority(5, True)


def test_parse_reads_an_explicit_boolean_false() -> None:
    assert parse_priority("u=5, i=?0") == Priority(5, False)


def test_parse_uses_defaults_when_members_are_absent() -> None:
    assert parse_priority("") == Priority(3, False)


def test_parse_defaults_the_incremental_flag_when_only_urgency_is_present() -> None:
    assert parse_priority("u=0") == Priority(0, False)


def test_parse_defaults_the_urgency_when_only_incremental_is_present() -> None:
    assert parse_priority("i") == Priority(3, True)


def test_parse_tolerates_surrounding_whitespace() -> None:
    assert parse_priority("  u=7 ,  i  ") == Priority(7, True)


def test_parse_ignores_unknown_members() -> None:
    assert parse_priority('u=2, x=9, s="k", i') == Priority(2, True)


def test_parse_falls_back_when_urgency_is_above_the_range() -> None:
    assert parse_priority("u=9") == Priority(3, False)


def test_parse_falls_back_when_urgency_is_below_the_range() -> None:
    assert parse_priority("u=-1") == Priority(3, False)


def test_parse_falls_back_when_urgency_is_not_an_integer() -> None:
    assert parse_priority("u=2.5") == Priority(3, False)


def test_parse_ignores_incremental_of_the_wrong_type() -> None:
    assert parse_priority("i=3") == Priority(3, False)


def test_parse_returns_defaults_for_a_malformed_header() -> None:
    assert parse_priority("!!! not a dictionary ###") == Priority(3, False)


def test_parse_keeps_the_last_value_of_a_repeated_key() -> None:
    assert parse_priority("u=1, u=6") == Priority(6, False)


def test_parse_ignores_the_whole_field_when_the_tail_is_malformed() -> None:
    # RFC 9651 section 4.2: a field that fails to parse is ignored as a whole.
    assert parse_priority("u=4, i, @broken") == Priority(3, False)


def test_parse_ignores_a_field_with_an_invalid_boolean() -> None:
    assert parse_priority("u=1, i=?2") == Priority(3, False)


def test_parse_ignores_a_field_with_a_trailing_comma() -> None:
    assert parse_priority("u=1,") == Priority(3, False)


def test_parse_ignores_a_field_with_a_leading_tab() -> None:
    # RFC 9651 discards only leading SP before a field value.
    assert parse_priority("\tu=1") == Priority(3, False)


def test_parse_ignores_a_field_with_an_integer_of_sixteen_digits() -> None:
    assert parse_priority("u=0000000000000001") == Priority(3, False)


def test_parse_accepts_an_integer_of_fifteen_digits() -> None:
    assert parse_priority("u=000000000000001") == Priority(1, False)


def test_parse_ignores_a_field_with_non_ascii_text() -> None:
    assert parse_priority('u=1, x="\u00e9"') == Priority(3, False)


def test_parse_ignores_a_field_with_members_not_separated_by_a_comma() -> None:
    assert parse_priority("u=1 i") == Priority(3, False)


def test_parse_reads_bytes_as_ascii() -> None:
    assert parse_priority(b"u=1, i") == Priority(1, True)
    assert parse_priority(bytearray(b"u=2")) == Priority(2, False)


def test_parse_ignores_bytes_outside_ascii() -> None:
    assert parse_priority(b"u=1, x=\xff") == Priority(3, False)


def test_parse_joins_several_field_lines() -> None:
    assert parse_priority(["u=1", "i"]) == Priority(1, True)
    assert parse_priority(("u=6", b"u=2")) == Priority(2, False)


def test_parse_treats_none_and_no_lines_as_an_absent_field() -> None:
    assert parse_priority(None) == Priority(3, False)
    assert parse_priority([]) == Priority(3, False)


def test_parse_rejects_other_types() -> None:
    for value in (3, 1.5, {"u": 1}, ["u=1", 2]):
        with pytest.raises(TypeError):
            parse_priority(value)  # type: ignore[arg-type]


def test_parse_ignores_an_urgency_of_the_wrong_type() -> None:
    for header in ("u=?1", "u=@1", "u=(1)", 'u="1"', "u=a", "u=:AQ==:"):
        assert parse_priority(header) == Priority(3, False), header


def test_parse_ignores_an_incremental_flag_of_the_wrong_type() -> None:
    for header in ("i=1", "i=(?1)", 'i="?1"', "i=a"):
        assert parse_priority(header) == Priority(3, False), header


def test_parse_reads_members_that_carry_parameters() -> None:
    assert parse_priority("u=2;a=1, i;b") == Priority(2, True)


def test_parse_tolerates_a_trailing_tab_after_the_last_member() -> None:
    assert parse_priority("u=1\t") == Priority(1, False)


def test_parse_reads_the_extremes_of_the_range() -> None:
    assert parse_priority("u=0") == Priority(0, False)
    assert parse_priority("u=7") == Priority(7, False)
    assert parse_priority("u=8") == Priority(3, False)


def test_a_later_invalid_urgency_cancels_an_earlier_valid_one() -> None:
    # The last value of a repeated key is the one the Dictionary keeps.
    assert parse_priority("u=1, u=9") == Priority(3, False)
