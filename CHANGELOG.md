# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.0] - 2026-10-21

The first stable release. The names in `priorityheader.__all__`, their parameter names,
defaults, return types and error types now follow semantic versioning; the
[GUIDE](https://github.com/JaviLianes8/priorityheader/blob/main/GUIDE.md) describes each
one. Code written for 0.2.0 keeps working unless it relied on one of the changes below.

### Changed

- `Priority` checks its fields whenever one is made, including through `_replace` and
  `_make`: an urgency outside 0..7 raises `PriorityError`, an urgency that is not an
  `int` or a flag that is not a `bool` raises `TypeError`. In 0.2.0 `Priority(9, "yes")`
  was accepted.
- `encode_h3_update` raises `FrameError` (still a `ValueError`) for a `target` name other
  than `"stream"` or `"push"`, instead of a plain `ValueError`, and `TypeError` for a
  `target` that is not a `str` (in 0.2.0 `None` or `5` raised `ValueError`). A `str`
  subclass is compared by its text, not by its own `__eq__`.
- The `strict` argument of `parse_priority`, `parse_params` and `PriorityUpdate.priority`
  takes only `True` or `False`; anything else raises `TypeError`. In 0.2.0 any truthy
  object, such as `"no"`, turned strict mode on.
- An object that claims to be a `bool` without being `True` or `False` (for example
  `unittest.mock.Mock(spec=bool)`) raises `TypeError` as an incremental flag or an
  extension value. In 0.2.0 it was stored as it was (and `build_priority` wrote it as a
  true flag); as an extension value it made comparing or hashing the `PriorityParams`
  that held it raise `RuntimeError`.
- `build_params` writes a `PriorityParams` subclass from the members the base class stores,
  checked again, so a subclass that overrides `urgency`, `incremental` or `extensions`
  can no longer make it write an invalid value.
- The command line ends a standard input line at LF only (dropping a CR before it). In
  0.2.0 the vertical tab, form feed, 0x1C to 0x1E, 0x85 and a lone CR also ended a line,
  so `--strict` accepted such a value from standard input and a `Priority` line of a
  message head was cut short.
- In a message head on standard input, a line that starts with a space or tab continues
  the field line before it (an obs-fold, RFC 9112 section 5.2) and is joined to it with
  one space, so a folded `Priority` value is read whole. Only spaces and tabs start such a
  line or are dropped around the break, and a blank one adds nothing. Such a line that
  follows no field line, for example right after the status line, is no field line and is
  dropped.
  In 0.2.0 each folded line was read on its own: the continuation of a `Priority` line
  was lost, so `--strict` accepted the value, and an indented `priority:` line counted.
- Error messages quote at most 60 characters of the value they mention. In 0.2.0 an
  oversized key, string or type error quoted the whole value, and an integer of more than
  4,300 digits (as an urgency, an extension value or a frame ID) raised Python's own
  `ValueError` about integer string conversion instead of `PriorityError` or
  `FrameError`.
- `Token`, `DisplayString` and `Date` show their type in `repr` (`Token('a')` instead of
  `'a'`), so `PriorityParams` reprs tell a Token from a String.
- `PriorityParams.over` raises `TypeError` for a `base` that is not a `Priority`; in
  0.2.0 a tuple or a string raised `AttributeError`.
- `build_priority` and `PriorityParams` raise `TypeError` for any `extensions` that is
  not a mapping. In 0.2.0 an empty or false value such as `0`, `""` or `[]` was read as
  no extensions.
- A tuple or list nested inside an inner list raises `TypeError` at any depth. In 0.2.0 a
  deeply nested or self-referencing list raised `RecursionError`.
- Decimals are parsed and written the same way whatever the caller's `decimal` context
  is. In 0.2.0 a lower precision or extra traps there made `parse_priority`,
  `build_priority` and `PriorityParams` raise `decimal` signals such as
  `InvalidOperation` or `Rounded`.
- A `str`, `bytes`, `bytearray` or `int` subclass whose `len`, slicing, `__bytes__`,
  `__buffer__` or `repr` raises still gets the documented result, not the subclass's own
  exception: `parse_priority`, `parse_params`, `merge_priority`, `decode_h2_update` and
  `decode_h3_update` read the stored text or octets of such a value, the builders write
  the stored octets of a Byte Sequence, and errors quote the stored value. A `__bytes__`
  or `__buffer__` that returns other octets changes nothing either. In 0.2.0 the parsers
  and decoders let the subclass's exception out or read the octets it returned.
- An error message stays within its 60-character quote when a value's `repr` returns a
  `str` subclass that misreports its length; in 0.2.0 the whole `repr` was quoted.

### Added

- `PriorityParams` can be pickled and copied; in 0.2.0 `pickle`, `copy.copy` and
  `copy.deepcopy` raised `TypeError`.
- `FrameError` takes an `offset`, set when an encoder refuses a value that does not parse
  and by `PriorityUpdate.priority(strict=True)`; it survives `pickle` and `copy` with
  `code` and `offset`, as `PriorityError` does.
- Docstrings with examples that run as tests, and a GUIDE.

## [0.2.0] - 2026-10-20

### Changed

- The field is parsed on the RFC 9651 grammar as a whole. A field that fails to parse is
  ignored and gives the defaults, as RFC 9218 section 4 requires; before, the members read
  ahead of the error were kept (`u=4, i, @broken` gave urgency 4, now 3).
- Integers longer than 15 digits, non-ASCII text, a leading tab, a trailing comma and
  members without a separating comma now make the field fail to parse.

### Added

- `parse_priority(..., strict=True)` raises `PriorityError` with the `offset` of the error.
- Input may be `bytes`, several field lines, or None for an absent field.
- `PriorityParams` and `parse_params`: the members a field carries, None when absent, with
  extension members kept in `extensions`.
- `merge_priority` and `PriorityParams.over`: response members over request values
  (RFC 9218 section 8).
- `build_params` writes exactly the members given, so a response can carry `u=3`;
  `build_priority` takes `extensions`. Both refuse what they cannot write back.
- PRIORITY_UPDATE frames: `encode_h2_update`, `decode_h2_update`, `encode_h3_update`,
  `decode_h3_update`, `PriorityUpdate` and `FrameError` with the RFC error code;
  `PriorityUpdate.priority(strict=True)` raises the code section 7 names.
- Structured field types `Token`, `Date` and `DisplayString` for extension values.
- `priorityheader` command line and `python -m priorityheader`.

## [0.1.0] - 2026-10-12

- First release, committed as 1574a93 and not uploaded to PyPI: parse and build the HTTP
  Priority header (RFC 9218), with the `u` urgency and `i` incremental members read from
  and written to an RFC 8941 structured-field dictionary, defaults applied on parse and
  omitted on build.

[Unreleased]: https://github.com/JaviLianes8/priorityheader/commits/main
[1.0.0]: https://github.com/JaviLianes8/priorityheader/compare/5477f81...main
[0.2.0]: https://github.com/JaviLianes8/priorityheader/compare/1574a93...5477f81
[0.1.0]: https://github.com/JaviLianes8/priorityheader/commit/1574a93
