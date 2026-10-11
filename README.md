# priorityheader

Parse and build the HTTP Priority header (RFC 9218), zero dependencies and typed.

## Install

```
pip install priorityheader
```

## Usage

```python
from priorityheader import Priority, build_priority, parse_priority

# Read an incoming header into an urgency and an incremental flag.
parse_priority("u=1, i")  # Priority(urgency=1, incremental=True)

# Absent members take their defaults: urgency 3, not incremental.
parse_priority("")  # Priority(urgency=3, incremental=False)

# The result is a tuple, so it unpacks.
urgency, incremental = parse_priority("u=5")  # (5, False)

# Parsing is tolerant: an out-of-range urgency, a wrong type, or a malformed
# header falls back to the defaults rather than raising.
parse_priority("u=9, junk")  # Priority(urgency=3, incremental=False)

# Build a header value, omitting anything left at its default.
build_priority(urgency=1)  # "u=1"
build_priority(urgency=0, incremental=True)  # "u=0, i"
build_priority()  # "" (default priority sends nothing)

# A boolean is rendered in its short form.
build_priority(incremental=True)  # "i"
```

Building validates the urgency: a value outside 0..7 raises `PriorityError`, and a
non-integer urgency or non-boolean flag raises `TypeError`.

## Why

RFC 9218 defines the HTTP `Priority` header as an RFC 8941 structured-field
dictionary with two members: `u`, an integer urgency from 0 (highest) to 7 (lowest,
default 3), and `i`, a boolean marking an incremental response (default false). The
rules are small but easy to get wrong by hand: the defaults, the 0..7 range, the
boolean short form, and dropping members that sit at their default so the value stays
compact.

No small Python package covers it. The structured-field machinery lives inside large
servers and SDKs (Tomcat in Java, the `sfv` crate in Rust), never shipped as a focused,
typed, dependency-free codec. This is that library: it reads a header into a typed
`Priority` tuple, applies the RFC defaults, tolerates anything malformed, and writes a
value back out with the defaults omitted, leaning only on the standard library.

## License

MIT. See [LICENSE](LICENSE).

## Links

- Website: https://lianes8studio.com
- GitHub: https://github.com/JaviLianes8
- LinkedIn: https://www.linkedin.com/in/jlianes/
