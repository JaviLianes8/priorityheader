# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0]

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
  `decode_h3_update`, `PriorityUpdate` and `FrameError` with the RFC error code.
- Structured field types `Token`, `Date` and `DisplayString` for extension values.
- `priorityheader` command line and `python -m priorityheader`.

## [0.1.0]

- First release: parse and build the HTTP Priority header (RFC 9218), with the
  `u` urgency and `i` incremental members read from and written to an RFC 8941
  structured-field dictionary, defaults applied on parse and omitted on build.
