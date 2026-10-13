"""Structured field Dictionaries, parsed as RFC 9651 section 4.2.2 describes."""

from __future__ import annotations

from ._sf import Reader, parse_bare_item, parse_key, parse_params
from ._sftypes import BareItem, InnerList, Member, Params

_OWS = " \t"


def parse_item(r: Reader) -> tuple[BareItem, Params]:
    """Parse an Item (a bare item and its parameters) at the cursor."""
    return parse_bare_item(r), parse_params(r)


def _inner_list(r: Reader) -> tuple[InnerList, Params]:
    r.pos += 1
    items: InnerList = []
    while not r.done():
        r.skip(" ")
        if r.peek() == ")":
            r.pos += 1
            return items, parse_params(r)
        items.append(parse_item(r))
        if r.peek() not in (" ", ")"):
            raise r.fail("inner list members are separated by spaces")
    raise r.fail("unterminated inner list")


def parse_dictionary(text: str) -> dict[str, Member]:
    """Parse a whole field value as a Dictionary; the last of repeated keys wins.

    Raises PriorityError with the offset where the value stopped following the grammar.
    """
    r = Reader(text)
    if not text.isascii():
        r.pos = next(index for index, char in enumerate(text) if not char.isascii())
        raise r.fail("structured fields are ASCII")
    r.skip(" ")
    members: dict[str, Member] = {}
    while not r.done():
        key = parse_key(r)
        member: Member
        if r.peek() == "=":
            r.pos += 1
            member = _inner_list(r) if r.peek() == "(" else parse_item(r)
        else:
            member = (True, parse_params(r))
        # RFC 9651: a repeated key overwrites the value but keeps the first position.
        members[key] = member
        r.skip(_OWS)
        if r.done():
            break
        if r.peek() != ",":
            raise r.fail("expected ','")
        r.pos += 1
        r.skip(_OWS)
        if r.done():
            raise r.fail("trailing comma")
    return members
