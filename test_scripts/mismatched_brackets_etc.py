from karp.foundation import json
from utils import markup_parser
from utils.salex import FieldWarning, SAOL, SO, is_visible
from dataclasses import dataclass
from tqdm import tqdm
import lark


@dataclass(frozen=True)
class MismatchedBrackets(FieldWarning):
    comment: str | None = None

    def collection(self):
        return "Extra"

    def category(self):
        return "Parenteser och citeringstecken"

    def to_dict(self):
        result = super().to_dict()
        if self.comment is not None:
            result["Info"] = self.comment
        return result


bracket_pairs = ["[]", "()", "{}", '""']
open_brackets = {s[0]: s[1] for s in bracket_pairs}
close_brackets = {s[1]: s[0] for s in bracket_pairs}


def brackets_ok(text):
    context = []

    for c in text:
        if c in open_brackets and c in close_brackets and context and context[-1] == c:  # matching "
            context = context[:-1]

        elif c in open_brackets:
            context.append(c)

        elif c in close_brackets:
            if context and context[-1] == close_brackets[c]:
                context = context[:-1]
            else:
                return False

    return not context


def quotes_ok(text):
    matches = 0

    for i, c in enumerate(text):
        if c != "'":
            continue
        prev_char = text[i - 1] if i > 0 else ""
        next_char = text[i + 1] if i < len(text) - 1 else ""

        if prev_char.isalpha() and next_char.isalpha():
            continue  # word-inner quote

        matches += 1

    return (matches % 2) == 0


def test_mismatched_brackets_etc(entries):
    for entry in tqdm(entries, desc="Checking bracket nesting"):
        for namespace in [SO, SAOL]:
            body = entry.entry.get(namespace.path, {})
            for path in json.all_paths(body):
                value = json.get_path(path, body)
                if not isinstance(value, str):
                    continue
                if not is_visible(path, body):
                    continue

                if path[-1] == "ordbildning":
                    text = value
                else:
                    try:
                        tree = markup_parser.parse(value)
                    except lark.LarkError:
                        yield MismatchedBrackets(entry, namespace, path, None, "ogiltig markup")
                        continue

                    text = markup_parser.text_contents(tree)

                if not brackets_ok(text):
                    yield MismatchedBrackets(
                        entry, namespace, path, None, "obalanserade parenteser eller citeringstecken"
                    )

                if not quotes_ok(text):
                    yield MismatchedBrackets(entry, namespace, path, None, "kolla citeringstecken")
