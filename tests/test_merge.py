from priorityheader import Priority, merge_priority


def test_a_response_urgency_replaces_the_client_urgency() -> None:
    assert merge_priority("u=5, i", "u=1") == Priority(1, True)


def test_an_absent_response_keeps_the_client_values() -> None:
    assert merge_priority("u=5, i", None) == Priority(5, True)
    assert merge_priority("u=5, i", "") == Priority(5, True)


def test_a_response_can_restore_the_defaults_explicitly() -> None:
    assert merge_priority("u=5, i", "u=3, i=?0") == Priority(3, False)


def test_an_absent_request_takes_the_defaults_before_merging() -> None:
    assert merge_priority(None, "i") == Priority(3, True)
    assert merge_priority(None, None) == Priority(3, False)


def test_invalid_response_members_keep_the_client_values() -> None:
    assert merge_priority("u=2, i", "u=9, i=5") == Priority(2, True)


def test_a_response_that_fails_to_parse_changes_nothing() -> None:
    assert merge_priority("u=2", "u=0,") == Priority(2, False)


def test_a_request_that_fails_to_parse_counts_as_default() -> None:
    assert merge_priority("u=2,", "i") == Priority(3, True)


def test_merge_accepts_field_lines_and_bytes() -> None:
    assert merge_priority([b"u=6", "i"], [b"u=0"]) == Priority(0, True)
