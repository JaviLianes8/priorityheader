import importlib.resources

import priorityheader

# The public API. Add every exported name here as the library grows; this list is the
# contract and the test below fails if the module and this list disagree.
PUBLIC_API: list[str] = [
    "DEFAULT_URGENCY",
    "H2_FRAME_TYPE",
    "H3_PUSH_FRAME_TYPE",
    "H3_REQUEST_FRAME_TYPE",
    "MAX_URGENCY",
    "MIN_URGENCY",
    "Date",
    "DisplayString",
    "ExtensionValue",
    "FieldInput",
    "FrameError",
    "Priority",
    "PriorityError",
    "PriorityParams",
    "PriorityUpdate",
    "Token",
    "build_params",
    "build_priority",
    "decode_h2_update",
    "decode_h3_update",
    "encode_h2_update",
    "encode_h3_update",
    "merge_priority",
    "parse_params",
    "parse_priority",
]


def test_all_lists_exactly_the_public_api() -> None:
    assert sorted(priorityheader.__all__) == sorted(PUBLIC_API)


def test_every_exported_name_resolves() -> None:
    for name in priorityheader.__all__:
        assert hasattr(priorityheader, name)


def test_version_is_a_three_part_string() -> None:
    parts = priorityheader.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_the_package_ships_type_information() -> None:
    assert importlib.resources.files("priorityheader").joinpath("py.typed").is_file()
