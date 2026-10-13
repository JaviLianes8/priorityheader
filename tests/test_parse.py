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
