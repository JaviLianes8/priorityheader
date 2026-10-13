# priorityheader improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 9218, RFC 9651, IANA HTTP Priority registry, RFC 9113, RFC 9114, RFC 9000, structured field test corpus
- [x] Structured field dictionary parser and serializer on RFC 9651, checked against the corpus
- [x] Priority parsing on the whole field: failure means defaults, strict mode raises
- [x] Response parameters and merging (RFC 9218 section 8)
- [x] Safe builder: request form, explicit form, extension parameters
- [x] PRIORITY_UPDATE frames for HTTP/2 and HTTP/3
- [x] Command line
- [x] Contracts: pinned sources, README examples, typing, installed wheel
- [x] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [x] Gates: ruff format, ruff check, mypy --strict, pytest
- [x] Mutation run: removing guarded logic makes the suite fail
- [x] Independent review findings fixed with regression tests
- [x] Pull request opened, guard clean

## Starting point

`0.1.0` gives `parse_priority`, `build_priority`, a `Priority` tuple and `PriorityError`.
The dictionary reader is best effort and keeps whatever parsed before the first error.
Probed against the sources below:

- RFC 9218 section 4 has receivers parse the Dictionary as RFC 9651 section 4.2 says, and
  RFC 9651 makes a field that fails to parse be ignored as a whole. Today the clean head
  survives: `u=4, i, @broken` gives urgency 4 and incremental, `u=1, i=?2` gives urgency 1,
  `u=1,` (trailing comma) gives urgency 1.
- The reader is looser than the grammar: a leading tab is skipped, a 16 digit Integer is
  accepted, non-ASCII text inside a String is accepted, `u=1 i` (no comma) keeps `u=1`,
  escapes other than `\"` and `\\` pass, byte sequences are not checked as base64.
- `bytes` input silently returns the defaults instead of being decoded (PRIORITY_UPDATE
  frames carry the value as ASCII octets) or refused.
- Several field lines cannot be passed; RFC 9651 combines them with a comma before parsing.
- No way to tell an absent member from a default one. RFC 9218 section 8 says the absence of
  a parameter in a response means the server does not want to change the client value, so
  merging needs that difference.
- The builder only writes the request form (defaults dropped). A server that wants to move a
  client from `u=5` back to `u=3` has to send `u=3`, which the builder cannot produce.
  Extension parameters (section 4.3) cannot be written either.
- No strict mode, no PRIORITY_UPDATE support, no command line, README examples are not run.

## Sources (fetched 2026-10-13)

- RFC 9218, https://www.rfc-editor.org/rfc/rfc9218.txt: parameters and receiver rules (4),
  urgency (4.1), incremental (4.2), extensions (4.3), the header field (5), PRIORITY_UPDATE
  (7, 7.1, 7.2), merging (8), server scheduling (10). Errata page
  https://www.rfc-editor.org/errata_search.php?rfc=9218: one report (7556, on the wording
  "descending order of priority"), rejected.
- RFC 9651, https://www.rfc-editor.org/rfc/rfc9651.txt: serialization (4.1) and parsing (4.2)
  of dictionaries, inner lists, parameters and bare items.
- IANA HTTP Priority registry, https://www.iana.org/assignments/http-priority/http-priority.xml
  (last updated 2022-06-09): exactly `u` and `i`.
- RFC 9113, https://www.rfc-editor.org/rfc/rfc9113.txt: frame header (4.1), FRAME_SIZE_ERROR
  for a frame too small for its mandatory data or above SETTINGS_MAX_FRAME_SIZE (4.2).
- RFC 9114, https://www.rfc-editor.org/rfc/rfc9114.txt: HTTP/3 frame layout and H3_FRAME_ERROR
  for payloads that are short or carry extra bytes (7.1).
- RFC 9000, https://www.rfc-editor.org/rfc/rfc9000.txt: variable-length integers (16) and the
  sample decodings of appendix A.1.
- Structured field test corpus, httpwg/structured-field-tests at commit
  781ba38464b2ec4c547e1e14d007d4f5ace7457e (dictionary, parameter, item, number, string,
  token, key, boolean, binary, date, display string, examples and the serialisation tests).
- None of these files is committed. `tests/upstream/MANIFEST.json` records URL, revision,
  size, sha256 and licence, `scripts/fetch_upstream.py` fetches and checks them into the
  ignored `tests/upstream/` folder, and their tests skip while they are absent.

## Ranked improvements

1. **Correct receiver semantics.** Parse the whole field on RFC 9651 section 4.2; a field
   that fails to parse gives the defaults (lenient) or raises `PriorityError` with an offset
   (`strict=True`). Unknown members, out-of-range urgency and wrong types are ignored in both
   modes, as section 4 requires. Several field lines are joined with a comma; `bytes` are read
   as ASCII.
2. **Structured field codec.** A dictionary parser and serializer for every RFC 9651 type
   (Integer, Decimal, String, Token, Byte Sequence, Boolean, Date, Display String, inner
   lists, parameters), checked against the httpwg corpus including the serialisation tests.
3. **Response parameters and merging.** `PriorityParams` keeps `None` for an absent member;
   `parse_params` reads it, `merge_priority` applies section 8 (a server value wins, an absent
   one keeps the client value), and `PriorityParams.over` does the same on parsed values.
4. **Safe builder.** `build_priority` keeps the request form (defaults omitted) and gains
   extension parameters; `build_params` writes exactly the members present, so a response
   can carry `u=3`. Keys and values are validated so the output always parses back to the
   same thing.
5. **PRIORITY_UPDATE frames.** Encode and decode the HTTP/2 frame (type 0x10, stream 0,
   non-zero prioritized stream, SETTINGS_MAX_FRAME_SIZE) and the HTTP/3 frames (0xF0700 for
   request streams, 0xF0701 for push IDs, varint fields, exact payload length), raising
   `FrameError` with the error code the RFCs name.
6. **Typed API.** Frozen value types, `Literal` codes, `mypy --strict` clean public surface,
   `py.typed`.
7. **Command line.** `priorityheader VALUE` prints the resolved priority as JSON;
   `--response` shows the explicit parameters, `--merge` combines a request and a response,
   `--strict` exits 1 on a value that does not parse. It fits: checking what a header means
   is a shell task.
8. **Contracts.** RFC examples, the IANA keys, the varint samples and the corpus are read
   from the pinned files; README examples run; the installed wheel and its console script are
   driven from an empty folder.
9. **Docs and packaging.** README with executed examples and an API table, CHANGELOG,
   keywords and classifiers, sdist without planning notes or fetched files.

## Out of scope

- A scheduler: RFC 9218 section 10 says no universal algorithm exists, so ordering responses
  stays with the server.
- Stream state tracking (idle, open, closed) and SETTINGS_MAX_CONCURRENT_STREAMS checks for
  PRIORITY_UPDATE: they need connection state the codec does not own.
- Structured field Lists at the top level: the Priority field is a Dictionary.

## Verification

- Gates on CPython 3.13.2: `ruff format --check .`, `ruff check .`, `mypy --strict src`
  (and `src tests`) and `pytest`, run on a fresh clone of the branch with the reference files
  fetched by `scripts/fetch_upstream.py` (every file matched the manifest). With
  `PRIORITYHEADER_E2E=1` the installed-wheel test builds the wheel and sdist, checks their
  contents (no planning notes, no fetched files, the manifest, the fetch script and the entry
  point present), installs the wheel in a fresh venv and drives the API, the
  `priorityheader` script and `python -m priorityheader` from an empty folder. Without the
  fetched files their tests skip and the rest of the suite passes.
- Guarded logic was changed one piece at a time (130 mutations, no bytecode written,
  `__pycache__` purged before each run, 180 s limit per mutant, baseline green before and
  after). The first run left 15 alive. Tests were added for ten: the last of repeated
  parameters, a byte sequence without padding, the message for a non-string key, type tags
  inside inner lists, deferring equality to the other operand, a non-ASCII octet in bytes
  input, the frame size boundary on both the encoder and the decoder, a head value after a
  tab, and an empty list of field lines (the guard was redundant and was removed). Five are
  equivalent: reading `?1` as "not `?0`" after the check that only `0` or `1` follow,
  wrapping a Date value that is already an int, the length check in front of the hex check
  of a Display String escape (a short escape fails as unterminated anyway), accepting a
  comma after an inner list member (the next item fails to parse), and a lower element ID
  bound for HTTP/3 below zero (the varint encoder refuses it).
- Seeded random round trips build 3000 parameter sets and 1000 request values and read them
  back strictly, 500 of each frame type round trip, and 5000 random strings and 5000 random
  octet strings go through the parsers and decoders without any undocumented exception.

## Review fixes

An independent review attacked the branch; each finding below is fixed with a test that
fails on the code before the fix (`tests/test_review_fixes.py` and the updated tests):

- A Decimal with a large exponent (`1e30`) raised `decimal.InvalidOperation` from the writer;
  the magnitude is now checked first and `PriorityError` is raised.
- Subclasses of `int`, `str` or `Token` that override `__str__` or `replace` could put CR LF
  into a built value. The writer now works on plain copies made through the base types,
  `PriorityParams` stores those copies, and the serialized dictionary is checked once more
  for characters a field line cannot carry.
- A Decimal with more than three decimal places was accepted and silently rounded, so it
  did not read back unchanged; the builders and `PriorityParams` now refuse it (the writer
  still rounds as RFC 9651 section 4.1.5 says).
- A Display String holding a lone surrogate raised `UnicodeEncodeError`; now `PriorityError`.
- `PriorityUpdate` records the protocol, and `priority(strict=True)` raises `FrameError`
  with `PROTOCOL_ERROR` (HTTP/2) or `H3_GENERAL_PROTOCOL_ERROR` (HTTP/3), the codes RFC 9218
  section 7 names for a value that does not parse.
- The command line took a broken value such as `u:1` on standard input for a header line and
  ignored it, even with `--strict`. Input now counts as a message head only when it starts
  with a status or request line or carries a Priority line.
- An unterminated escape reported an offset past the end of the value; offsets are now
  clamped to the length of the text.
- The corpus run now includes the List files (`list`, `listlist`, `param-list`,
  `param-listlist`), which exercise the inner list and item readers.
- `_sf.py` was split (types and character sets moved to `_sftypes.py`) so it stays well
  under the 200 line limit.

## Second mutation run

After the review fixes the gates, the corpus, the installed-wheel test and the mutation run
were repeated on a fresh clone on a second machine (CPython 3.14.2; every fetched file
matched the manifest). 149 mutations, baseline green before and after; 11 survived. Tests
were added for five (`tests/test_writer_hardening.py`): a Decimal that rounds up to 13
integer digits, a key subclass that lies in `__str__` and `__format__`, a Date subclass that
lies in `__int__`, the item writer called on its own with a lying int, and a message head
without a Priority line in strict mode. Each was checked to fail with its mutant applied.
The other six are equivalent: the four listed for the first run that still apply (`?1`
reading, the Date wrap in the reader, the comma after an inner list member, the HTTP/3
lower bound), keeping the plain urgency returned by the check (the writer makes its own
plain copy), and the last check of the serialized dictionary for control characters (every
earlier step already refuses them; it stays as a second line of defence).
