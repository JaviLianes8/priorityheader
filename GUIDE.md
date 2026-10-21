# priorityheader guide

The behaviour of every public name in detail. Each Python block below runs as a test: a
comment line after a `print` holds what it prints.

## Reading a field

`parse_priority` and `parse_params` read the `Priority` field of RFC 9218 section 5. The
field value is an RFC 9651 Dictionary, and the two parsers differ only in what they
return for a member that is absent.

- `parse_priority` gives a `Priority` with the defaults filled in (urgency 3, not
  incremental), which is what a request and a PRIORITY_UPDATE frame mean.
- `parse_params` gives a `PriorityParams` with None for each absent member, which is what
  a response needs (see the next section).

The input is a field value (`str`), its octets (`bytes` or `bytearray`, read as Latin-1
so a non-ASCII octet fails the grammar at its position), a list of the values of several
field lines (joined with `", "` first, as RFC 9651 section 4.2 says), or None for an
absent field. Any other type raises `TypeError`.

What happens to a value depends on where it goes wrong:

- A value that breaks the Dictionary grammar is ignored as a whole, as RFC 9651 section
  4.2 requires: the result is the defaults (or all None). With `strict=True` the parser
  raises `PriorityError` instead, with `offset` set to the index where reading stopped.
- Once the Dictionary parses, a `u` that is not an Integer in 0..7 and an `i` that is not
  a Boolean are ignored, in both modes (RFC 9218 sections 4.1 and 4.2). A repeated key
  keeps its last value.
- Every other member is kept in `PriorityParams.extensions`, without its parameters.

```python
from priorityheader import PriorityError, parse_params, parse_priority

print(parse_priority("u=0, i=?1, u=6"))
# Priority(urgency=6, incremental=True)
print(parse_params("u=8, i=1, hint=(1 2)"))
# PriorityParams(urgency=None, incremental=None, extensions={'hint': (1, 2)})
print(parse_priority(["u=1", "i=?2"]))
# Priority(urgency=3, incremental=False)
try:
    parse_priority(["u=1", "i=?2"], strict=True)
except PriorityError as error:
    print(error.offset, error)
# 8 a Boolean is ?0 or ?1 at offset 8
```

Offsets count in the joined text when several lines are given. Leading spaces are
allowed and a leading tab is not, as in RFC 9651 section 4.2; HTTP stacks strip
whitespace around a field value before it reaches you.

## Requests, responses and merging

RFC 9218 section 8 lets a server answer with its own `Priority` field. There an absent
member means "keep the value the client asked for", not "use the default". So a server
that wants to move a client from urgency 5 back to 3 has to send `u=3`.

`merge_priority(request, response)` resolves the request with the defaults and lays
every member the response carries over it. `PriorityParams.over(base)` does the same with
values already parsed, and `resolve()` is `over(Priority())`. Both fields are read in the
lenient mode, and either may be None.

```python
from priorityheader import Priority, merge_priority, parse_params

print(merge_priority("u=5, i", "u=3"))
# Priority(urgency=3, incremental=True)
print(merge_priority("u=5, i", None))
# Priority(urgency=5, incremental=True)
response = parse_params("i=?0")
print(response.over(Priority(1, True)), response.resolve())
# Priority(urgency=1, incremental=False) Priority(urgency=3, incremental=False)
```

## Building a field value

`build_priority(urgency=3, incremental=False, *, extensions=None)` writes the request
form: members at their default are left out, so the default priority is the empty string
(send no field at all). `build_params(params)` writes exactly the members a
`PriorityParams` holds, defaults included, which a response needs.

Extension members (RFC 9218 section 4.3) take any RFC 9651 bare item, or a tuple of them
for an inner list:

| Python value | Written as |
| --- | --- |
| `bool` | `?1` / `?0` (a member that is `True` is written as the bare key) |
| `int` | Integer, at most 15 digits |
| `decimal.Decimal` | Decimal, at most 12 integer and 3 fraction digits |
| `str` | String of printable ASCII |
| `Token` | Token |
| `bytes` | Byte Sequence (base64) |
| `Date` | Date, `@` and whole seconds |
| `DisplayString` | Display String, percent-encoded UTF-8 |
| `tuple` of the above | Inner list |

Keys must be RFC 9651 keys (lower-case letter or `*`, then lower-case letters, digits,
`_`, `-`, `.`, `*`) and cannot be `u` or `i`. Everything is checked before anything is
written, so the result always parses back to what was given: a value out of range, a key
that is not a key or a character a field cannot carry raises `PriorityError`, and a wrong
type raises `TypeError`. A float is refused: use `Decimal`.

```python
from decimal import Decimal

from priorityheader import Date, PriorityParams, Token, build_params, build_priority

print(build_priority(1, True, extensions={"hint": (Token("lcp"), Decimal("0.5"))}))
# u=1, i, hint=(lcp 0.5)
print(build_params(PriorityParams(incremental=False, extensions={"since": Date(0)})))
# i=?0, since=@0
```

## PRIORITY_UPDATE frames

`encode_h2_update(stream_id, field_value, *, max_frame_size=16384)` and
`decode_h2_update(frame, *, max_frame_size=16384)` handle the HTTP/2 frame of RFC 9218
section 7.1 (type 0x10), header included. `encode_h3_update(element_id, field_value, *,
target="stream")` and `decode_h3_update(frame)` handle the HTTP/3 frames of section 7.2:
0xF0700 for a request stream and 0xF0701 for a push ID.

The encoders refuse a value that does not parse, since a receiver may close the
connection over it. The decoders return a `PriorityUpdate` record and leave the value as
sent; `PriorityUpdate.priority()` reads it, and with `strict=True` turns a broken value
into the connection error section 7 allows.

`FrameError.code` names the error the RFCs assign:

| Situation | `code` |
| --- | --- |
| HTTP/2 frame on a stream other than 0, prioritized stream ID 0 | `PROTOCOL_ERROR` |
| HTTP/2 payload under 4 bytes or over `max_frame_size` | `FRAME_SIZE_ERROR` |
| HTTP/3 payload that ends inside the element ID | `H3_FRAME_ERROR` |
| HTTP/3 request variant naming a stream that is not a request stream | `H3_ID_ERROR` |
| Broken value, `priority(strict=True)` on HTTP/2 / HTTP/3 | `PROTOCOL_ERROR` / `H3_GENERAL_PROTOCOL_ERROR` |
| Field value given to an encoder that does not parse (`offset` set) | None |
| Not exactly one PRIORITY_UPDATE frame, or an argument out of range | None |

Stream state, stream limits and push ID limits belong to the connection and stay with
the caller.

```python
from priorityheader import FrameError, decode_h3_update, encode_h3_update

frame = encode_h3_update(4, "u=7")
print(frame.hex(), decode_h3_update(frame).priority())
# 800f07000404753d37 Priority(urgency=7, incremental=False)
try:
    decode_h3_update(bytes.fromhex("800f07000405753d37"))
except FrameError as error:
    print(error.code)
# H3_ID_ERROR
```

## The value types

`Priority` is a named tuple whose fields are checked whenever one is made, including by
`_replace` and `_make`: `PriorityError` for an urgency outside 0..7, `TypeError` for an
urgency that is not an `int` or a flag that is not a `bool`. `PriorityParams` is
immutable, hashable and compares by value, telling `True` from `1` and a `Token` from a
`str` because they are written differently. `PriorityUpdate` is a plain record. All of
them, and both errors, survive `pickle` and `copy`.

`Token`, `DisplayString` (both `str`) and `Date` (an `int`) mark the structured field type
of a value; they compare equal to the plain value and show their type in `repr`.

```python
from priorityheader import Priority, PriorityParams, Token

print(PriorityParams(extensions={"a": Token("x")}) == PriorityParams(extensions={"a": "x"}))
# False
print(Priority(2, False)._replace(incremental=True))
# Priority(urgency=2, incremental=True)
```

## Errors

`PriorityError` is a `ValueError`; `FrameError` is a `PriorityError`. `offset` is set when
a value failed to parse at a position (a strict parse, or a value an encoder refuses),
`code` when an RFC names the connection error.
Messages quote at most 60 characters of any value, and building them never fails, so a
huge or hostile input cannot turn an error into a different one. Wrong argument types
raise `TypeError`: `strict` takes only `True` or `False`, and the `target` of
`encode_h3_update` only a `str`.

## Command line

`priorityheader VALUE...` prints what the field lines ask for as JSON: urgency,
incremental flag, extension members in their written form and the canonical request
form. `--response` prints the explicit members with null for absent ones, and
`--request VALUE` merges the given lines, as a response, over that request. Without a
value the lines come from standard input, either one bare value per line or a message
head such as `curl -sI` prints (then only its `Priority` lines count, a folded line
joined to the one before it with a space). Only LF ends a line. `--strict` exits
with status 1 on a value that does not parse; usage errors exit with 2.

## Stability

From 1.0.0 the names in `priorityheader.__all__`, their parameter names, defaults,
return types and error types follow semantic versioning. Everything in a module whose
name starts with an underscore is private.

## How it is checked

The structured field reader and writer pass the httpwg structured field test corpus. The
RFC texts and the IANA registry are fetched by `scripts/fetch_upstream.py` and checked
against their recorded hashes before the tests read them. The tests also compare the
library live with independent implementations when they are installed: http-sf for
Dictionaries, hyperframe for HTTP/2 frames and aioquic for HTTP/3 frames and QUIC
variable-length integers.
