from lark import Lark, Transformer
from typing import Union, Iterator
from dataclasses import dataclass

Tree = list[Union[str, "Tag"]]


@dataclass
class Tag:
    tag: str
    contents: Tree


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
    markup = lambda _, args: args
    tag = lambda _, args: Tag(tag=args[0].value, contents=args[1])
    text = lambda _, args: args[0].value
    TEXT = lambda _, tok: tok.update(value=tok.replace(r"\[", "[").replace(r"\]", "]").replace(r"\\", "\\"))


parser = Lark(GRAMMAR, parser="lalr", transformer=MarkupTransformer())


@dataclass
class Fragment:
    text: str
    tags: list[str]


def text_fragments(text: Union[str, "Tree"], tags=None) -> Iterator[Fragment]:
    """
    Returns the text contained in a markup string or tree, but where each text is
    annotated with the tags it's surrounded by. E.g.:

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
