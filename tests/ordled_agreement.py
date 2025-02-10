from utils.testing import Tester, PerEntryWarning, per_entry

class OrdledWarning(PerEntryWarning):
    ordled: str

    @classmethod
    def identifier_fields(cls):
        return super().identifier_fields() | {"ordled"}

class OrdledTester(Tester):
    warning_cls = OrdledWarning

    @per_entry
    def test(self, entry):
        ortografi = entry.get("ortografi")
        ordled = entry.get("saol", {}).get("ordled")

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
                yield OrdledWarning(ordled=ordled)
