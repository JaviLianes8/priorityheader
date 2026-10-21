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
- [ ] Five QA lenses (item 19): round 6 findings (lenses a, c, e) fixed in 0d74275
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
| 10 | Supported Pythons | PASS: CPython 3.10.19, 3.11.5, 3.12.12, 3.13.2, 3.14.2, 3.14.2t at e4abedd; 3.10.19, 3.11.14, 3.12.12, 3.13.11, 3.14.2, 3.14.2t again at db2f1e5; 3.8 and 3.9 refused by `requires-python` |
| 11 | README and `twine check` | PASS: `twine check --strict`, absolute links, badge |
| 12 | Dated CHANGELOG section | PASS: 1.0.0, 2026-10-21 |
| 13 | pyproject 1.0.0, Production/Stable | PASS |
| 14 | sdist and wheel contents | PASS |
| 15 | Gates each exit 0 | PASS: see Gates |
| 16 | Independent reviewer | pending |
| 17 | PR and trace guard | PR #3 from `release/1.0.0`, trace guard CLEAN; merge and publish left to the maintainer |
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
`FrameError` for an unknown `target` name and `TypeError` for a `target` that is not a
`str`; `strict` takes only a `bool`; fake bools refused; `build_params` rechecks a
subclass; LF-only standard input lines in the command line; bounded messages;
type-showing reprs. Public classes keep their defining module, as in 0.2.0 (round 4 undid
a rewrite to `priorityheader` that broke `typing.get_type_hints` and `inspect.getsource`).
Added: pickling and copying of `PriorityParams`, an `offset` on `FrameError`. Internal: the frame module split into `_frames`, `_h2` and
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
`tests/test_cli_folds.py` times the command line's head reader on 20,000 and 80,000 folded
lines: linear, and no slower than the same count of unfolded `Priority` lines.
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

## QA lenses (item 19)

### Round 1 (on 5f8b037)

Lenses a, c and e reported findings; every one is fixed in c94810e, none is disputed.

| Lens | Finding | Fix | Contract |
| --- | --- | --- | --- |
| a F1 | `PriorityUpdate.priority` example never ran: classes re-homed to `priorityheader` hide their methods from the doctest collector | the suite walks `__all__` and every method docstring itself and pins the example count per object (60 examples) | `tests/test_docstrings.py`; fails when that example's expected output is broken |
| a F2 | `Priority._field_defaults` was `{}` (0.2.0: both defaults) | defaults declared on the named tuple fields | `test_priority_keeps_the_named_tuple_field_defaults` |
| a F3 | `PriorityParams.over` raised `AttributeError` for a non-Priority | `TypeError` naming the value | `test_over_takes_only_a_priority` |
| a F4 | CHANGELOG missed the error pickling fix; 0.2.0 and 0.1.0 undated; no link references | entries added, 0.2.0 dated from PyPI (2026-10-20), 0.1.0 from its commit 1574a93 (2026-10-12, never on PyPI), link references for every section | `test_every_changelog_release_is_dated_and_linked` |
| c F1 | caller's `decimal` context leaked `InvalidOperation`, `Rounded`, `Inexact` out of parse and build | the parser builds a Decimal from its text; the writer rounds in a private context and compares without context arithmetic | `test_the_caller_decimal_context_changes_nothing`, `test_too_many_decimal_places_stay_a_priority_error_in_any_context` (prec 6, Rounded and Inexact trapped) |
| c F2 | deep or self-referencing lists raised `RecursionError` | a list inside an inner list is refused with `TypeError` without recursing | `test_nesting_beyond_an_inner_list_is_a_type_error_at_any_depth` |
| c F3 | falsy non-mappings (`0`, `""`, `[]`...) accepted as `extensions` | only None means no extensions | `test_extensions_that_are_not_a_mapping_are_refused_even_when_empty` |
| c F4 | `shown` called a subclass's `len` and slicing | length and cut go through the base type, the whole quote is guarded | `test_a_subclass_that_breaks_len_still_gets_the_documented_type_error` |
| e F1 | M51, M56, M61, M62, M74, M94, M97, M116 only died with the fetched corpus | hand-written grammar cases that need no fetched file | `tests/test_contract_corpus_free.py` |
| e F2 | M101, M102: decoders could lose non-ASCII payload octets | exact `field_value` and strict offset for a 0xFF octet, both protocols | `test_h2_decode_keeps_every_payload_octet_as_sent`, `test_h3_decode_keeps_every_payload_octet_as_sent` |
| e F3 | M77: HTTP/3 decoder accepting type 0x10 survived | ten other frame types refused | `test_h3_decode_takes_only_the_two_priority_update_types` |
| e F4 | M83: huge-int guard in `shown` untested | the "an int of N bits" wording, with and without the int string limit | `test_a_huge_int_is_described_by_its_bit_count_in_every_message` |

Every new test failed on 5f8b037 where it pins a behaviour change (a F2, a F3, a F4, c F1
to c F4) or was run against its mutant: the twelve mutants above (M51, M56, M61, M62, M74,
M94, M97, M116, M101, M102, M77, M83) and the broken `PriorityUpdate.priority` example
each make the new tests fail. Behaviour changes are in the CHANGELOG under 1.0.0.

Gates at c94810e on another machine (CPython 3.14.2, fresh clone, fetched sources and the
three reference implementations present): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (460 passed, 2 opt-in e2e
skipped) all exit 0.

### Round 2 (on b6e03d5)

Lenses a, c and e confirmed every round 1 finding fixed and reported the findings below;
every one is fixed in bddbe63, none is disputed.

| Lens | Finding | Fix | Contract |
| --- | --- | --- | --- |
| a N1 | CHANGELOG said hostile `str`/`bytes` subclasses get the documented result, but `parse_priority` and `parse_params` let a subclass's `len` or slicing exception out (as 0.2.0 did) | the parsers read a plain copy (`str.__str__`, `bytes(memoryview(...))`) of each field line; CHANGELOG entry rewritten to state the parser change against 0.2.0 | `test_the_parsers_read_a_hostile_str_subclass_as_its_plain_text`, `test_the_parsers_read_a_hostile_bytes_subclass_as_its_plain_octets` |
| c F5 | a `repr` returning a `str` subclass that misreports its length reached the message whole (1 MB) | `shown` cuts the `repr` text as a plain `str`; CHANGELOG entry added | `test_a_repr_that_lies_about_its_length_is_still_cut` (Priority, build_priority, encode_h2_update, over, decode_h2_update, decode_h3_update) |
| e N27 | `+` after `@` in a Date survived the strict parser mutant | strict offsets and lenient drop for `@+5` in a member, an inner list and a parameter, `@x` and a bare `@` | `test_a_date_takes_no_plus_sign_and_needs_a_digit` |
| e N10 | the 60-character quote limit was only bounded loosely | exact quoted text for a long str, bytes, list and dict | `test_a_message_quotes_at_most_sixty_characters` |
| e N01 | bit-count wording tested at one size | 193, 201, 14,300, 20,001 and 50,001 bits through three entry points, and exact digits at 192 bits | `test_an_int_above_192_bits_is_described_by_its_bit_count`, `test_an_int_of_192_bits_is_quoted_by_its_digits` |
| e N02 to N05, N11 | base-type routing in `shown` tested only by exception type | exact message for str, bytes and bytearray subclasses whose `len` raises a `BaseException` subclass, an int subclass whose `bit_length` raises, and a value whose `repr` raises | `test_a_hostile_str_or_bytes_subclass_is_quoted_as_its_plain_value`, `test_a_hostile_int_subclass_is_described_by_the_bit_count_of_its_plain_value`, `test_a_value_whose_repr_fails_is_named_by_its_type` |

All of them live in `tests/test_quoting_contract.py`. The N1 and F5 tests failed on
b6e03d5 before the fix. Each reviewer mutant was then applied to the fixed code one at a
time, and each one makes that file fail: N27 (`"-+"` sign), N10 (`QUOTE_LIMIT + 10`), N01
(threshold 100,000 bits), N02, N03 and N04 (no base copy), N05 (`value.bit_length()`), N11
(fallback without the type name), plus reverting each fix (F5, N1 for str, N1 for bytes).

Gates at bddbe63 on another machine (CPython 3.14.2, fresh clone, fetched sources and the
three reference implementations present): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (490 passed, 2 opt-in e2e
skipped) all exit 0.

### Round 3 (on 33172b6)

Lens a confirmed N1 fixed and reported one finding; it is fixed in db2f1e5 and not
disputed. The lens c and lens e re-checks of this round left no verdict and run again on
the fixed commit.

| Lens | Finding | Fix | Contract |
| --- | --- | --- | --- |
| a N2 | `decode_h2_update` and `decode_h3_update` copied a frame with `bytes(frame)`, which runs a subclass's `__bytes__`: its exception escaped and a `__bytes__` returning other octets changed what was decoded, against the CHANGELOG line about hostile subclasses | one helper, `plain_octets`, copies the stored octets with the base type's own slice, so neither `__bytes__` nor a Python `__buffer__` (3.12 and later, which `memoryview` would call) runs; the frame decoders, the parsers, the Byte Sequence writer and the message quoting all use it; CHANGELOG line rewritten to name the decoders and `__buffer__` | `tests/test_plain_octets_contract.py`: decoders, parsers, builder and messages with `bytes` and `bytearray` subclasses whose `__bytes__` and `__buffer__` raise or return other octets |

The new tests failed on 33172b6 (10 of 11). Each of the six call sites was then put back
to its old conversion one at a time on the fixed code (`bytes(frame)` in the decoders,
`bytes(value)` in the parser and the writer, `memoryview` in the helper and in both
quoting branches), and each one makes the contract files fail.

Gates at db2f1e5 on another machine (CPython 3.14.2, fresh clone, fetched sources, the
three reference implementations, `PRIORITYHEADER_E2E=1` and `PRIORITYHEADER_E2E_PYPI=1`):
`ruff format --check .`, `ruff check .`, `mypy --strict src`, `mypy --strict src tests`
and `pytest` (503 passed, no skips) all exit 0.

Interpreters at db2f1e5, on another machine from a fresh clone: one build, `twine check
--strict` passed for both files, the wheel listing identical to the one at e4abedd and the
sdist listing differing only by the five test files added since; the wheel installed in a fresh venv per interpreter and the sdist's suite run
with `src` removed and the fetched sources present: CPython 3.11.14, 3.12.12, 3.13.11 and
3.14.2 (481 passed), 3.10.19 and 3.14.2t (480 passed, aioquic 1.7.0 has no wheel there).
The skips are the opt-in e2e tests and the two mypy tests (mypy is not installed in those
venvs; it runs in the gates above). Doctests pass from each install. 3.9.25 refuses the
wheel.

### Round 4 (on 56cf946)

Lenses a, c, d and e reported the findings below; every one is fixed in 509798a, none is
disputed. Lens d passed everything else; its one finding was the timing test.

| Lens | Finding | Fix | Contract |
| --- | --- | --- | --- |
| a F1 | `typing.get_type_hints(PriorityUpdate)` raised `NameError` (`Target`), so a pydantic model with a `PriorityUpdate` field could not be built; 0.2.0 resolved it | the `__module__` rewrite to `priorityheader` is gone from all eight public classes, so string annotations resolve in their defining module again; CHANGELOG line about it removed | `tests/test_contract_introspection.py`: `get_type_hints` on every public class, function and method, and the exact `PriorityUpdate` field types |
| a F2 | `inspect.getsource` was wrong or raised for 7 of the 8 public classes | same fix | `test_the_source_of_every_public_class_is_its_own_definition`, `test_every_public_class_is_reached_from_the_package` (replaces the old `__module__` test) |
| a F3 | CHANGELOG claimed 0.2.0 could not unpickle a `FrameError` with a code; it could | entry removed; only the new `offset` is claimed | none (docs) |
| a F4 | GUIDE and `encode_h3_update` promised `TypeError` for wrong types, but a non-str `target` raised `FrameError` and `strict` took any object by truthiness | `TypeError` for a `target` that is not a `str` (a `str` subclass is compared by its text) and for a `strict` that is not `True` or `False`, in `parse_priority`, `parse_params` and `PriorityUpdate.priority`; GUIDE, docstrings and CHANGELOG say so | `tests/test_contract_arguments.py`: `test_a_target_that_is_not_a_str_is_a_type_error`, `test_a_target_is_compared_by_its_plain_text`, `test_strict_must_be_a_bool`, `test_strict_takes_both_bools` |
| a F5 | README said the raw octets of a frame are read | "or a field value as bytes" | none (docs) |
| a F6 | README wrote `parse_priority(value, strict=True)` | `parse_priority(header, strict=True)` | none (docs) |
| a F7 | the encoders' "value does not parse" error (code None, offset set) was missing from the `FrameError` docstring and the GUIDE table | docstring, table row and the GUIDE errors paragraph updated | none (docs) |
| c F1 | the command line split standard input with `str.splitlines()`, so 0x0B, 0x0C, 0x1C to 0x1E, 0x85 and a lone CR ended a line: `--strict` passed such a value and a head's `Priority` line was cut short | only LF ends a line, one CR before it is dropped; every other octet reaches the parser and fails with its offset; CHANGELOG entry | `test_only_a_line_feed_ends_a_standard_input_line` (each octet, bare value and message head, strict exit 1 at offset 3, lenient fallback) |
| c F2 | `Mock(spec=bool)` was stored as an incremental flag or extension value, then `==` and `hash` raised `RuntimeError` | flags are checked by identity with `True` and `False` (one helper, also used for `strict`); the writer refuses an object that only claims `bool`; the equality tag falls back to the type of the value instead of raising | `test_a_fake_bool_is_refused_as_the_incremental_flag`, `test_a_fake_bool_is_refused_as_an_extension_value`, `test_stored_flags_are_the_bool_singletons` |
| c F3 | `build_params` rendered a subclass's overridden `urgency`, `incremental` and `extensions` unchecked (`u=99, i="yes", u=5, i=1.235`) | it reads the base class slots and builds a fresh `PriorityParams` from them, which runs every check again; an uninitialised subclass raises `TypeError` | `test_build_params_writes_what_the_base_instance_holds`, `test_build_params_rechecks_a_subclass_that_corrupts_its_members` |
| d D1 | `test_parsing_time_grows_linearly` compared wall-clock times and failed about 1 run in 30 under load | it measures CPU time per call (`time.process_time`), repeats each sample for at least 0.2 s because that clock ticks every 15.6 ms on Windows, pauses the collector, measures both sizes in turn and keeps the best of three; the bound is 10x (linear is about 4x, quadratic 16x) | the test itself; run alone the ratios are 3.5 to 4.6 |
| e F1-E15 | the writer's Date range was not pinned | Date at plus and minus 999,999,999,999,999 written; plus and minus 10^15 and 10^16 refused by `build_priority` and `PriorityParams` | `test_the_writer_takes_the_whole_date_range_and_nothing_more` |
| e F2-J07 | the OWS strip of standard input lines was not pinned | tab and space around bare values, CRLF line ends | `test_optional_whitespace_around_a_standard_input_line_is_dropped` |
| e F3-F05 | long bytes values could be quoted from their own `repr` | exact message for a 100-byte `bytes` and `bytearray` subclass whose `repr` is forged | `test_a_long_bytes_value_is_quoted_from_its_octets_never_its_repr` |
| e F4-C06 | HTAB inside an inner list was pinned only by the optional http-sf oracle | strict offsets and lenient drop for a tab after `(`, between items and before `)` | `test_strict_parse_refuses_grammar_breaks_at_their_offset` |
| e F5 | C02, D12, D13 and T03 were pinned only by the fetched corpus | a repeated key keeps its first place and its last value; invalid UTF-8 in a Display String, a Date with a fraction and an upper-case key letter fail at their offsets | `test_a_repeated_key_keeps_its_first_place_and_its_last_value`, `test_strict_parse_refuses_grammar_breaks_at_their_offset` |

The behaviour tests (a F1, a F2, a F4, c F1, c F2, c F3) failed on 56cf946 before the fix.
On 509798a, on another machine from a bundle of the commit with the fetched sources, each
of the eight reviewer mutants (E15, J07, F05, C06, C02, D12, D13, T03) and each fix put
back on its own (the `__module__` rewrite on `PriorityUpdate` and on `Token`, the `target`
type check, the `strict` check, `splitlines`, `isinstance` for flags, `isinstance` in the
writer, rendering the subclass's own properties) makes its contract file fail. The
corpus-free cases were written by hand from the RFC 9651 grammar.

Gates at 509798a on another machine (CPython 3.14.2, fresh clone of the commit, fetched
sources, http-sf, hyperframe, aioquic, `PRIORITYHEADER_E2E=1` and
`PRIORITYHEADER_E2E_PYPI=1`): `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (586 passed, no skips) all exit 0. The timing test
then ran in three processes at once pinned to two cores, six rounds: 18 runs, no failure.

### Round 5 (on f96684a)

Lens a re-checked its seven round 4 findings and lens c its three: all fixed. Lens e
re-ran its mutation round. The new findings below are fixed in 150bbe0, none is disputed.

| Lens | Finding | Fix | Contract |
| --- | --- | --- | --- |
| a N1 | CHANGELOG said a `PriorityParams` holding a `Mock(spec=bool)` raised `RuntimeError` on `==` and `hash` in 0.2.0; that was true only for an extension value (as the incremental flag it hashed and compared, and `build_priority` wrote it as `i`) | entry limited to extension values; checked again on the 0.2.0 wheel | none (docs) |
| c F4 | in a message head on standard input an obs-fold of the `Priority` line was read as a separate line and dropped, so `priority: u=1` folded onto ` i` passed `--strict` with urgency 1 | in a head, a line starting with SP or HTAB is joined to the field line before it with one SP (RFC 9112 section 5.2); after anything else it is dropped (section 2.2), and an indented `priority:` line no longer marks a head; GUIDE and CHANGELOG say so | `tests/test_cli_lines.py`: `test_a_folded_priority_line_is_one_value` (SP, HTAB and mixed folds: strict exit 1 at offset 4, lenient defaults), `test_a_fold_keeps_a_valid_value_valid`, `test_a_fold_belongs_to_the_field_before_it`, `test_an_indented_line_that_continues_no_field_is_no_priority_line`, `test_bare_values_are_not_folded` |
| e N1-S11 | dropping every CR before LF instead of one survived the suite | contract added | `test_only_one_carriage_return_before_a_line_feed_is_dropped` (bare and head, strict exit 1 at offset 3, lenient defaults) |
| e N2-S13-S14 | dropping only the leading OWS of a start line, or stripping before dropping the CR, survived the suite | contract added | `test_a_request_line_with_trailing_whitespace_starts_a_head` (SP, HTAB and both, CRLF and LF: strict exit 0 with the defaults) |

The c F4 contracts failed on f96684a before the fix (nine failures; the CR and start
line contracts pass there, as lens e expected). On the fixed code each
of these mutants of `_cli.py` makes `tests/test_cli_lines.py` fail: S11
(`rstrip("\r")`), S13 (`lstrip` on the stripped lines), no folding at all, folding only on
SP, joining without the SP, a fold after any line, appending a fold as its own line, and
detecting the head from the unfolded lines.
Each mutant ran against `tests/test_cli.py`, `tests/test_cli_lines.py`,
`tests/test_fuzz.py` and `tests/test_review_fixes.py`. The CHANGELOG entries were checked
against the 0.2.0 wheel: a folded `Priority` line, an indented `priority:` line after the
status line and a fold after another field all gave exit 0 with the unfolded urgency there.

Gates at 150bbe0 on another checkout (CPython 3.13.2, clone of a bundle of the commit,
fetched sources, http-sf, hyperframe, aioquic, `PRIORITYHEADER_E2E=1` and
`PRIORITYHEADER_E2E_PYPI=1`): `ruff format --check .`, `ruff check .`, `mypy --strict src`,
`mypy --strict src tests` and `pytest` (604 tests, the 586 of round 4 and 18 new) all
exit 0.

### Round 6 (on d76d240)

Lens a re-checked N1 and lens c re-checked F1 to F4: all fixed. Lens e re-ran its
mutation round. The findings below are fixed in 0d74275, none is disputed. Lens a's
EVIDENCE item is its evidence notes, not a defect, and needs no change.

| Lens | Finding | Fix | Contract |
| --- | --- | --- | --- |
| a N2, c F5 | the obs-fold join of 150bbe0 rebuilt the whole field line for every continuation, so the standard input reader took quadratic time in the number of folds (400,000 folds: 71.8 s in the reader, 63.5 s end to end) | `_cli._unfold` collects the pieces of each field line in a list and joins them once; the result is the same (a seeded differential of 200,000 random line lists against the old join, compared after the OWS strip the reader applies: 0 mismatches). 400,000 folds now take 0.14 s in the reader and 0.9 s end to end with `--strict` | `test_reading_folds_takes_linear_time`: 80,000 folds take under 10 times as long as 20,000 (measured 3.9 to 4.1, was 13 to 15) and under 3 times as long as 80,000 unfolded `Priority` lines (measured 0.3) |
| e F1-M03-M04 | nothing pinned that only SP and HTAB start a fold | contract added | `test_only_a_space_or_a_tab_starts_a_fold` (CR, VT, FF, 0x1C, 0x1F, 0x85 and 0xA0 after a `Priority` line: strict exit 0, urgency 1) |
| e F2-M36-M37 | nothing pinned that the join trims only SP and HTAB | contract added | `test_a_fold_trims_only_spaces_and_tabs` (VT, FF and 0x85 at the end of the folded line and at either end of the continuation: strict exit 1 at offsets 3, 4 and 7) |
| e F3-M16 | nothing pinned that the OWS before the line break belongs to the obs-fold | contract added | `test_whitespace_before_the_line_break_belongs_to_the_fold` (SP, HTAB and mixed before the break inside a string: `x="a b"`; before a bare continuation: strict exit 1 at offset 4) |
| e F4-M42 | nothing pinned that a blank continuation keeps the fold going | contract added | `test_a_blank_continuation_does_not_end_the_fold` (SP, HTAB and mixed blank lines: `u=1, i` read whole, `u=1 i` refused at offset 4) |
| e F5-M25 | nothing pinned that the field name is exactly `priority` | contract added | `test_only_the_priority_field_name_counts` (`priority-hint`, `priorityx`, `xpriority`, `priorities`, `priorit`: the defaults) |

The CHANGELOG fold entry now says that only spaces and tabs start a fold or are dropped
around the break and that a blank one adds nothing (the same behaviour as 150bbe0, now
pinned). The timing contract failed on d76d240 before the fix (80,000 folds took 0.48 s
to 0.50 s against 0.034 s to 0.036 s for 20,000); the other new contracts pin behaviour
that was already right and pass there. On the fixed code each of these mutants of
`_cli.py` makes `tests/test_cli_folds.py` fail: M03 (CR starts a fold), M04
(`isspace()`), M36 (`rstrip()` on the folded line), M37 (`strip()` on the continuation),
M16 (no `rstrip` before the join), M42 (a blank line ends the fold), M25
(`startswith("priority")`), keeping blank pieces in the join, and joining again on every
fold (the quadratic form).

Gates at 0d74275 on another machine (CPython 3.14.6, clone of a bundle of the commit,
fetched sources, http-sf 1.4.0, hyperframe 6.1.0, aioquic 1.7.0, `PRIORITYHEADER_E2E=1`
and `PRIORITYHEADER_E2E_PYPI=1`): `ruff format --check .`, `ruff check .`,
`mypy --strict src`, `mypy --strict src tests` and `pytest` (632 passed, the 604 of round
5 and 28 new, no skips) all exit 0. The timing contract then ran six more times there:
six passes.

### Disputed findings

None in round 1, round 2, round 3, round 4, round 5 or round 6.
