# priorityheader

[![Lianes8 Certified](https://lianes8studio.com/certified/lianes8-certified-badge.svg)](https://lianes8studio.com/certified)

Parse, merge and build the HTTP `Priority` field and PRIORITY_UPDATE frames (RFC 9218),
zero dependencies and typed. The [GUIDE](https://github.com/JaviLianes8/priorityheader/blob/main/GUIDE.md)
describes every public name in detail, and the
[CHANGELOG](https://github.com/JaviLianes8/priorityheader/blob/main/CHANGELOG.md) what
changed in each release.

## Install

```
pip install priorityheader
```

## Read a request

```python
from priorityheader import Priority, parse_priority

print(parse_priority("u=1, i"))
# Priority(urgency=1, incremental=True)

# Absent members take their defaults: urgency 3, not incremental.
print(parse_priority(None))
# Priority(urgency=3, incremental=False)

# Unknown members, an urgency outside 0..7 and wrong types are ignored.
print(parse_priority("u=9, i, vendor-hint=?1"))
# Priority(urgency=3, incremental=True)

# A field that breaks the structured field grammar is ignored as a whole.
print(parse_priority("u=1, i=?2"))
# Priority(urgency=3, incremental=False)

# Several field lines, or the raw octets of a frame, are read too.
print(parse_priority(["u=2", b"i"]))
# Priority(urgency=2, incremental=True)
```

`parse_priority(value, strict=True)` raises `PriorityError` instead of falling back when
the field does not parse; the error carries the `offset` where reading stopped. Out of
range and mistyped members are still ignored, because RFC 9218 says a receiver must ignore
them once the dictionary parses.

## Merge a response into a request

In a request an absent member means its default. In a response it means the server has no
opinion, so the client value stands (RFC 9218 section 8).

```python
from priorityheader import Priority, merge_priority, parse_params

print(merge_priority("u=5, i", "u=1"))
# Priority(urgency=1, incremental=True)

params = parse_params("u=1")
print(params)
# PriorityParams(urgency=1, incremental=None)
print(params.over(Priority(5, True)))
# Priority(urgency=1, incremental=True)
```

## Build a field value

```python
from priorityheader import PriorityParams, Token, build_params, build_priority

# Request form: members at their default are left out.
print(repr(build_priority()))
# ''
print(build_priority(urgency=0, incremental=True))
# u=0, i
print(build_priority(1, extensions={"vendor-hint": Token("viewport")}))
# u=1, vendor-hint=viewport

# Response form: exactly the members given, defaults included.
print(build_params(PriorityParams(urgency=3, incremental=False)))
# u=3, i=?0
```

Both builders check every key and value, so the result always parses back to what was
given: an urgency outside 0..7 or an extension that cannot be written raises
`PriorityError`, and a wrong type raises `TypeError`. A carriage return or line feed can
never reach the output. `Priority` checks its fields the same way.

## PRIORITY_UPDATE frames

```python
from priorityheader import decode_h2_update, decode_h3_update, encode_h2_update, encode_h3_update

frame = encode_h2_update(5, "u=0")
print(frame.hex())
# 00000710000000000000000005753d30
update = decode_h2_update(frame)
print(update)
# PriorityUpdate(element_id=5, field_value='u=0', target='stream', protocol='h2')
print(update.priority())
# Priority(urgency=0, incremental=False)

push = decode_h3_update(encode_h3_update(3, "u=6", target="push"))
print(push.target, push.priority().urgency)
# push 6
```

The decoders raise `FrameError`, whose `code` names the connection error the RFCs assign:
`PROTOCOL_ERROR` or `FRAME_SIZE_ERROR` for HTTP/2, `H3_FRAME_ERROR` or `H3_ID_ERROR` for
HTTP/3, and None for bytes that are not a single PRIORITY_UPDATE frame.
`update.priority(strict=True)` raises a `FrameError` with `PROTOCOL_ERROR` or
`H3_GENERAL_PROTOCOL_ERROR` when the carried value does not parse, the error RFC 9218
allows a server to close the connection with. Stream state and stream limits belong to the
connection and stay with the caller.

## Command line

```
$ priorityheader "u=1, i"
{
  "urgency": 1,
  "incremental": true,
  "extensions": {},
  "canonical": "u=1, i"
}
$ curl -sI https://example.com | priorityheader --response
$ priorityheader --request "u=5, i" "u=1"
```

Without a value the field lines come from standard input, either bare values or a message
head. `--strict` exits with status 1 on a value that does not parse; usage errors exit
with 2.

## API

| Name | What it does |
| --- | --- |
| `parse_priority(header, *, strict=False)` | Resolved `Priority` of a request or frame field |
| `parse_params(header, *, strict=False)` | Members present in a field, `None` when absent |
| `merge_priority(request, response)` | Response members over the request (section 8) |
| `build_priority(urgency=3, incremental=False, *, extensions=None)` | Request form, defaults left out |
| `build_params(params)` | Exactly the members of a `PriorityParams` |
| `encode_h2_update(stream_id, field_value, *, max_frame_size=16384)` | HTTP/2 PRIORITY_UPDATE frame (type 0x10) |
| `decode_h2_update(frame, *, max_frame_size=16384)` | One HTTP/2 frame into a `PriorityUpdate` |
| `encode_h3_update(element_id, field_value, *, target="stream")` | HTTP/3 PRIORITY_UPDATE frame (0xF0700, 0xF0701) |
| `decode_h3_update(frame)` | One HTTP/3 frame into a `PriorityUpdate` |
| `Priority` | Checked named tuple of `urgency` and `incremental` |
| `PriorityParams` | Immutable members of a field, with `over()` and `resolve()` |
| `PriorityUpdate` | Decoded frame: `element_id`, `field_value`, `target`, `protocol`, `priority()` |
| `PriorityError` | A `ValueError`, with the `offset` of a strict parse failure |
| `FrameError` | A `PriorityError` with the RFC error `code` |
| `Token`, `Date`, `DisplayString` | Structured field types for extension values |
| `ExtensionValue`, `FieldInput` | Type aliases for extension values and field input |
| `DEFAULT_URGENCY`, `MIN_URGENCY`, `MAX_URGENCY` | 3, 0 and 7 |
| `H2_FRAME_TYPE`, `H3_REQUEST_FRAME_TYPE`, `H3_PUSH_FRAME_TYPE` | Frame type numbers |

## Why

RFC 9218 replaced the HTTP/2 dependency tree with two small signals: an urgency from 0
(first) to 7 (background) and a flag saying the response is useful in pieces. They travel
as a structured field dictionary in the `Priority` field, end to end, and in
PRIORITY_UPDATE frames, hop by hop. The rules are short but easy to get subtly wrong: a
field that fails to parse must be dropped as a whole, unknown or out of range members are
ignored, an absent member means the default in a request but "no change" in a response,
and a response that wants the default urgency has to say `u=3` out loud.

In Python the pieces exist apart. http-sf and http_sfv parse and write any structured
field, but leave the Priority rules (defaults, ignored members, the section 8 merge) to
you; both also accept a 16 digit Integer with a leading zero, which RFC 9651 says to
refuse, and http-sf refuses a Byte Sequence without padding, which RFC 9651 says
parsers should read. hyperframe 6.1.0 has no PRIORITY_UPDATE frame type and the
HTTP/3 frame types of aioquic 1.7.0 do not include it either. This library is the
focused piece: a parser that passes the httpwg structured field test corpus and is
compared live with http-sf, a builder that refuses anything it cannot write back, the
section 8 merge, and the frame codecs checked against hyperframe and aioquic, using only
the standard library.

## Development

`python scripts/fetch_upstream.py` downloads the RFCs, the IANA registry and the
structured field test corpus the tests compare against; they are not part of the
repository and their tests skip until fetched. The comparisons with other
implementations run when `http-sf`, `hyperframe` and `aioquic` are installed, and skip
otherwise. `scripts/check.ps1` runs format, lint, types and tests.

## License

MIT. See [LICENSE](https://github.com/JaviLianes8/priorityheader/blob/main/LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
