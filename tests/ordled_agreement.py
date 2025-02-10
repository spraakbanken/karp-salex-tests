from utils.testing import Tester, Warning
from utils.salex import entry_name, SAOL

class OrdledWarning(Warning):
    ordled: str

    @property
    def identifier(self):
        return (self.entry_id, self.ord, self.ordled)

class OrdledTester(Tester):
    warning_cls = OrdledWarning

    def test(self, entry):
        ortografi = entry.entry.get("ortografi")
        ordled = entry.entry.get("saol", {}).get("ordled")

        replacements = {
            "·": "",
            "|": "",
#            "bbb": "bb", # comment out these two so that we get some test failures
#            "ttt": "tt",
            "sss": "ss",
            "lll": "ll",
            "rrr": "rr",
            "fff": "ff",
            "ppp": "pp",
            "ddd": "dd",
            "ggg": "gg",
            "nnn": "nn",
            "mmm": "mm",
        }

        if ortografi and ordled:
            squashed_ordled = ordled

            for k, v in replacements.items():
                squashed_ordled = squashed_ordled.replace(k, v)

            if ortografi != squashed_ordled:
                yield OrdledWarning(entry_id=entry.id, ord=entry_name(entry, SAOL), ordled=ordled)
