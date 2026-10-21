# priorityheader 1.0.0 certification report

The 1.0.0 certification bar (19 items) applied to priorityheader. PyPI has 0.2.0, which is
byte for byte the `main` branch at 5477f81 (the wheel's modules compared with the tree), so
every change listed here is a change against the PyPI release.

Progress:
- [x] Branch `release/1.0.0` created from `main` (5477f81, same code as PyPI 0.2.0)
- [x] Baseline gates on 0.2.0
- [x] API review and 1.0.0 changes (item 1)
- [x] Errors, typing, docstrings and doctests (items 2 to 5)
- [x] Ground truth: fetched sources re-fetched, reference implementations run live (item 7)
- [x] Contract, fuzz and author mutation round (items 6, 9, 18)
- [x] Docs: README, GUIDE, CHANGELOG (items 11, 12)
- [x] Packaging, e2e and upgrade from PyPI 0.2.0, every Python (items 8, 10, 13, 14)
- [x] Gates (item 15)
- [x] PR and trace guard
- [ ] Five QA lenses (item 19)
- [ ] Independent reviewer (item 16)

## Scorecard (author)

| # | Item | Result |
| --- | --- | --- |
| 1 | Public API reviewed for stability | PASS: 25 names kept from 0.2.0 with their parameter names; signatures pinned in `tests/test_contract_api.py`; changes in CHANGELOG and GUIDE |
| 2 | `__all__` exact, no private imports in docs | PASS |
| 3 | Docstrings with runnable examples | PASS: every public function and class; constants and aliases in the package docstring; README (16 outputs) and GUIDE (13) run as tests |
| 4 | Typed end to end | PASS: `mypy --strict src tests`, `py.typed`, revealed types checked from a consumer snippet |
| 5 | Typed, documented, bounded errors | PASS: `PriorityError` (a `ValueError`) with `offset`, `FrameError` with `code` and `offset`, `TypeError` for wrong types; messages quote at most 60 characters |
| 6 | Contract tests of every public name | PASS |
| 7 | Real ground truth | PASS: 30 fetched sources re-fetched and hash-checked on 2026-10-21; http-sf, hyperframe, aioquic run live |
| 8 | Real e2e from the wheel | PASS: wheel in a fresh venv driven from an empty folder, CLI by subprocess, PyPI 0.2.0 upgraded in place |
| 9 | Seeded fuzz, no crash, hang or blowup | PASS |
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t; 3.8 and 3.9 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-20 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
| 18 | Contracts bite (mutations) | PASS: author 40, 38 killed, 2 argued equivalent |
| 19 | Five independent QA lenses | pending |

## Baseline on 0.2.0 (before any change)

Fresh clone at 5477f81 on another machine, CPython 3.14, fetched sources present and
`PRIORITYHEADER_E2E=1`: `ruff format --check .`, `ruff check .`, `mypy --strict src tests`
exit 0; `pytest` 282 passed. No public docstring had an example.

Defects found in 0.2.0 by reproducing them:

- An integer of more than 4,300 digits as an urgency, an extension value or a frame ID
  raised Python's own `ValueError` about integer string conversion, not `PriorityError`.
- Error messages quoted whole values: a 100,000 character urgency of the wrong type gave a
  100,030 character message; the same for keys, Strings, Tokens and `target`.
- `copy.copy`, `copy.deepcopy` and `pickle` of a `PriorityParams` raised `TypeError`.
- `Priority(9, "yes")` was accepted, so an impossible priority could be passed around.
- `encode_h3_update` raised a plain `ValueError` for an unknown `target`.
- `Token("a")` printed as `'a'`, so a `PriorityParams` repr hid the Token/String difference.
- `python -m priorityheader` ran the program on import (no `__main__` guard), which also
  stopped doctest collection; the README linked LICENSE relatively; there was no GUIDE.

## API review (item 1)

Kept: all 25 public names of 0.2.0, their parameter names (`header`, `request`,
`response`, `urgency`, `incremental`, `extensions`, `params`, `stream_id`, `element_id`,
`field_value`, `frame`, `max_frame_size`, `target`, `strict`) and defaults. Changed (all in
the CHANGELOG): `Priority` checks its fields, including through `_replace` and `_make`;
`FrameError` for an unknown `target`; bounded messages; type-showing reprs; public classes
report `priorityheader` as their module. Added: pickling and copying of `PriorityParams`,
an `offset` on `FrameError`. Internal: the frame module split into `_frames`, `_h2` and
`_h3` to keep every file under 200 lines with the examples.

## Ground truth (item 7)

- Fetched sources (`tests/upstream/MANIFEST.json`: URL, revision, size, sha256, licence):
  RFC 9218, RFC 9651, RFC 9113, RFC 9114, RFC 9000, the IANA HTTP Priority registry and 24
  files of the httpwg structured-field-tests corpus at commit 781ba38. First fetched on
  2026-10-13; re-fetched by `scripts/fetch_upstream.py` on 2026-10-21, all 30 matching
  their hashes. Nothing fetched is committed or shipped.
- http-sf 1.4.0 (`tests/test_oracles.py`): 60,000 seeded fields (valid, one edit off,
  noise). 52,394 cases agree (23,157 accepted by both with identical values, types and
  parameters, 29,237 refused by both). 7,605 are the oracle's own limits, each re-checked:
  Dates it cannot turn into a datetime on this platform and Byte Sequences without padding
  (RFC 9651 section 4.2.7: parsers SHOULD NOT fail on them); our canonical form must read
  back identically. 1 case is an oracle deviation: http-sf accepts a 16 digit Integer with
  a leading zero, which RFC 9651 section 4.2.4 step 5 refuses; without the zeros both agree.
  Also 10,000 generated Dictionaries built by `build_params` read back through http-sf
  with the same values, and its serializer gives our text.
- hyperframe 6.1.0 (`tests/test_oracles_frames.py`): 3,000 encoded HTTP/2 frames parsed by
  its frame header and body parser: type 0x10, stream 0, flags 0, length and payload.
- aioquic 1.7.0: 3,000 varints identical to `encode_uint_var`, read back by our decoder;
  HTTP/3 frames identical to its `encode_frame` for both targets, and decoded back.

## Fuzz and hostile input (item 9)

`tests/test_fuzz.py`, seeds 11 to 13: 60,000 fields (lenient never raises, strict raises
only `PriorityError` with an offset inside the input and a short message, strict and
lenient agree, bytes read like text); 30,000 build round trips in both forms; 30,000
merges against a member-by-member model; 15,000 frame round trips and random bytes into
both decoders (only `FrameError`); 1,500 command lines (exit 0 with JSON or 1 with a short
message). Fourteen hostile shapes timed at 20,000 and 80,000 units: linear.
`tests/test_contract_api.py` covers 100,000 character and 5,000 digit inputs and an object
whose `repr` raises, on every error path.

## Author mutation round (item 18)

40 mutants over every module, each applied alone to a fresh clone of the pushed branch on
another machine, the full suite run with `-x`, a 300 s per-test limit, the fetched sources
and the three oracles present. The first round killed 36. M34 and M39 survived: contracts
in `tests/test_contract_edges.py` (f72dfec) now kill both on a re-run. M35 and M38 are
equivalent: every character before the first non-ASCII one is ASCII, so Latin-1 and UTF-8
stop at the same offset; and a Decimal with 13 integer digits is refused by the range
check that follows.

| Id | File | Mutation | Result | First test that failed |
| --- | --- | --- | --- | --- |
| M01 | `_model.py` | builder urgency range off by one | killed | test_build::test_build_renders_the_highest_urgency |
| M02 | `_parse.py` | reader accepts urgency 8 | killed | test_docs::test_every_example_runs_and_prints_its_comment |
| M03 | `_parse.py` | Boolean or Date read as urgency | killed | test_fuzz::test_parsing_never_crashes_and_strict_agrees_with_lenient |
| M04 | `_parse.py` | non-Boolean i read as a flag | killed | test_docs::test_every_example_runs_and_prints_its_comment |
| M05 | `_parse.py` | merge arguments swapped | killed | doctest `merge_priority` |
| M06 | `_parse.py` | field lines joined without the space | killed | test_docs::test_every_example_runs_and_prints_its_comment |
| M07 | `_build.py` | request form writes u=3 | killed | doctest package |
| M08 | `_build.py` | request form writes i=?0 | killed | doctest package |
| M09 | `_sfwrite.py` | writer Integer range off by one | killed | test_sf_corpus::test_the_corpus_file_serializes_to_its_canonical_form |
| M10 | `_sfwrite.py` | String backslash not escaped | killed | test_build::test_build_writes_every_extension_type |
| M11 | `_sf.py` | reader Integer digit limit off by one | killed | test_fuzz::test_parsing_never_crashes_and_strict_agrees_with_lenient |
| M12 | `_sf.py` | reader Decimal fraction limit off by one | killed | test_fuzz::test_parsing_never_crashes_and_strict_agrees_with_lenient |
| M13 | `_sfdict.py` | trailing comma accepted | killed | doctest `PriorityError` |
| M14 | `_sfdict.py` | leading tab accepted | killed | test_oracles::test_dictionaries_read_like_http_sf |
| M15 | `_h2.py` | reserved bit of the frame stream not ignored | killed | test_frames::test_h2_decode_ignores_the_reserved_bits_and_the_flags |
| M16 | `_h2.py` | 3 byte payload accepted | killed | test_frames::test_h2_decode_errors_carry_the_rfc_code |
| M17 | `_h2.py` | stream ID little-endian | killed | doctest `encode_h2_update` |
| M18 | `_h2.py` | frame size limit off by one | killed | test_frames::test_h2_decode_allows_a_payload_of_exactly_the_frame_size |
| M19 | `_h2.py` | prioritized stream reserved bit kept | killed | test_frames::test_h2_decode_ignores_the_reserved_bits_and_the_flags |
| M20 | `_h3.py` | varint size boundary off by one | killed | test_frames_h3::test_varints_use_the_fewest_bytes |
| M21 | `_h3.py` | request stream check too weak | killed | test_frames_h3::test_h3_decode_errors_carry_the_rfc_code |
| M22 | `_h3.py` | frame types swapped | killed | doctest `PriorityUpdate` |
| M23 | `_h3.py` | varint prefix bits not masked | killed | test_frames_h3::test_h3_decode_accepts_non_minimal_varints |
| M24 | `_frames.py` | strict error codes swapped | killed | test_review_fixes::test_a_strict_frame_value_failure_carries_the_connection_error_code |
| M25 | `_frames.py` | encoder sends a value that does not parse | killed | test_contract_api::test_frame_errors_carry_the_offset_of_a_broken_value |
| M26 | `_errors.py` | messages quote whole values | killed | test_contract_api::test_errors_are_typed_and_messages_stay_short |
| M27 | `_errors.py` | hostile repr escapes | killed | test_contract_api::test_errors_are_typed_and_messages_stay_short |
| M28 | `_model.py` | `_make` and `_replace` skip the checks | killed | test_contract_api::test_priority_checks_every_way_of_building_it |
| M29 | `_model.py` | pickling drops extensions | killed | test_contract_api::test_values_survive_pickle_and_copy |
| M30 | `_model.py` | equality does not tell True from 1 | killed | test_docs::test_every_example_runs_and_prints_its_comment |
| M31 | `_model.py` | i accepted as an extension | killed | test_build::test_build_refuses_unsafe_extensions |
| M32 | `_sfwrite.py` | Display String quote not escaped | killed | test_fuzz::test_what_parses_builds_back_to_the_same_members |
| M33 | `_cli.py` | header name compared with case | killed | test_cli::test_standard_input_takes_a_message_head |
| M34 | `_sf.py` | padding not normalised | killed (re-run) | test_contract_edges::test_byte_sequences_the_corpus_lets_a_parser_accept_are_read |
| M35 | `_parse.py` | octets decoded as UTF-8 | equivalent | - |
| M36 | `_sfdict.py` | first of a repeated key wins | killed | test_docs::test_every_example_runs_and_prints_its_comment |
| M37 | `_sf.py` | first of a repeated parameter wins | killed | test_oracles::test_dictionaries_read_like_http_sf |
| M38 | `_sfwrite.py` | writer Decimal digit limit off by one | equivalent | - |
| M39 | `_build.py` | `build_params` duck-types its argument | killed (re-run) | test_contract_edges::test_build_params_takes_only_priority_params |
| M40 | `_h2.py` | encoder accepts stream 0 | killed | test_frames::test_h2_encode_refuses_stream_ids_outside_1_to_2_31 |

## Packaging, e2e and Pythons (items 8, 10, 13, 14)

- `tests/test_e2e_wheel.py` with `PRIORITYHEADER_E2E=1` and `PRIORITYHEADER_E2E_PYPI=1`:
  builds wheel and sdist, inspects both, installs the wheel in a fresh venv and drives the
  library and the CLI (script and `python -m`) from an empty folder with `-I`; installs
  0.2.0 from PyPI, checks it, upgrades it in place to the built wheel and checks the 0.2.0
  calls, the 1.0.0 program and the CLI again.
- Wheel: the package, `py.typed`, the entry point and `licenses/LICENSE`, nothing else.
  sdist: sources, tests, scripts, docs, LICENSE and the manifest; no fetched files, no
  scratch, no round notes. `twine check --strict` passes for both.
- At e4abedd on this PC, one build, the wheel installed in a fresh venv per interpreter and
  the sdist's own suite run with `src` removed (fetched sources present): CPython 3.10.19
  (379 passed, 3 skipped), 3.11.5, 3.12.12, 3.13.2, 3.14.2 (380 passed, 2 skipped) and
  3.14.2t (379 passed, 3 skipped); the skips are the two opt-in e2e tests and, on 3.10 and
  3.14t, the frame oracle (aioquic 1.7.0 has no wheel there). Doctests pass from each
  install. 3.8.20 and 3.9.25 refuse the wheel.

## Gates (item 15)

At e4abedd on another machine from a fresh clone, CPython 3.14, each command on its own,
with the fetched sources, http-sf, hyperframe, aioquic, `PRIORITYHEADER_E2E=1` and
`PRIORITYHEADER_E2E_PYPI=1`: `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (400 passed, no skips) all exit 0.
