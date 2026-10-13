# priorityheader improvement round

Progress:
- [x] Brainstorm ranked improvements (this file)
- [x] Pin the ground truth: RFC 9218, RFC 9651, IANA HTTP Priority registry, RFC 9113, RFC 9114, RFC 9000, structured field test corpus
- [x] Structured field dictionary parser and serializer on RFC 9651, checked against the corpus
- [x] Priority parsing on the whole field: failure means defaults, strict mode raises
- [x] Response parameters and merging (RFC 9218 section 8)
- [ ] Safe builder: request form, explicit form, extension parameters
- [ ] PRIORITY_UPDATE frames for HTTP/2 and HTTP/3
- [ ] Command line
- [ ] Contracts: pinned sources, README examples, typing, installed wheel
- [ ] Docs and packaging: README, CHANGELOG, metadata, sdist contents
- [ ] Gates: ruff format, ruff check, mypy --strict, pytest
- [ ] Mutation run: removing guarded logic makes the suite fail
- [ ] Independent review findings fixed with regression tests
- [ ] Pull request opened, guard clean

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
