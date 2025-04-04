"""A parser for the [b markup format] used in [i Salex]."""

from lark import Lark, Transformer, LarkError
from typing import Union, Iterator
from dataclasses import dataclass

Markup = list[Union[str, "Element"]]


@dataclass
class Element:
    tag: str
    contents: Markup


def parse(text: str) -> Markup:
    """
    Parse a markup string.

    Example:

    >>> parse("hello [i this is] [b a simple [sup test]]")
    ['hello ',
     Element(tag='i', contents=['this is']),
     ' ',
     Element(tag='b',
             contents=['a simple ', Element(tag='sup', contents=['test'])])]
    """

    return parser.parse(text)


GRAMMAR = r"""
    ?start: markup
    markup: element*
    ?element: "[" TAG " " markup "]" -> tag
            | TEXT -> text
    TAG: "b" | "i" | "u" | "caps" | "r" | "rp" | "sup" | "sub" | "källa"
    TEXT: (ESCAPED_CHAR | UNESCAPED_CHAR)+
    ESCAPED_CHAR: "\\" /./
    UNESCAPED_CHAR: /[^\[\]\\]/
"""


class MarkupTransformer(Transformer):
    markup = lambda _, args: args  # noqa: E731
    tag = lambda _, args: Element(tag=args[0].value, contents=args[1])  # noqa: E731
    text = lambda _, args: args[0].value  # noqa: E731
    TEXT = lambda _, tok: tok.update(value=tok.replace(r"\[", "[").replace(r"\]", "]").replace(r"\\", "\\"))  # noqa: E731


parser = Lark(GRAMMAR, parser="lalr", transformer=MarkupTransformer())


@dataclass
class Fragment:
    """A piece of text annotated with which tags it's surrounded by."""

    text: str
    tags: list[str]


def text_fragments(text: Union[str, "Markup"], tags=None) -> Iterator[Fragment]:
    """
    Returns the text contained in a markup string or tree, but where each text is
    annotated with the tags it's surrounded by.

    Example:

    >>> for fragment in text_fragments("hi [rp bla [i again]] [sub more]"): print(fragment)
    Fragment(text='hi ', tags=[])
    Fragment(text='bla ', tags=['rp'])
    Fragment(text='again', tags=['rp', 'i'])
    Fragment(text=' ', tags=[])
    Fragment(text='more', tags=['sub'])
    """

    if tags is None:
        tags = []
    if isinstance(text, str):
        text = parser.parse(text)

    for elt in text:
        if isinstance(elt, str):
            yield Fragment(elt, tags)
        else:
            if not elt.contents:  # special case for empty tags
                yield Fragment("", tags + [elt.tag])
            else:
                yield from text_fragments(elt.contents, tags + [elt.tag])


def text_contents(text: Union[str, "Markup"]) -> str:
    """
    Returns the text contained in a markup string or tree.
    """

    return "".join(fragment.text for fragment in text_fragments(text))


def to_markup(text: Union[str, "Markup"]) -> str:
    """
    Convert a tree back to markup text.
    """
    if isinstance(text, str):
        return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")

    elif isinstance(text, list):
        return "".join(to_markup(elt) for elt in text)

    else:
        return f"[{text.tag} {to_markup(text.contents)}]"


def strip_markup(text: Union[str, "Markup"]) -> str:
    """
    Strip all markup from a markup string, returning plain text.
    """
    try:
        tree = parser.parse(text)
        return text_contents(tree)
    except LarkError:
        return text
