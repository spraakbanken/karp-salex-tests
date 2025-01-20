"""Support for running tests and generating warnings."""

# Not yet working

import karp.foundation.json as json
from karp_api import *
from copy import deepcopy
import pydantic
from karp.search.domain import QueryRequest


class Warning(pydantic.BaseModel):
    # TODO: resource id
    entry_id: str
    entry_version: int
    test_name: str
    test_results: list[dict]
    status: str

    @classmethod
    def make(cls, entry, test_name, test_results):
        return cls(
            entry_id=entry.id, entry_version=entry.version, test_name=test_name, test_results=test_results, status="new"
        )


def find_existing_warning(test_resource, resource, warning):
    query = QueryRequest(
        resources=[test_resource],
        q=f"and(equals|entry_id|{warning.entry_id}||equals|test_name|{warning.test_name})",
        lexicon_stats=False,
    )

    results = es_search_service.query(query)
    # fetch results from MariaDB because Elasticsearch may not store data exactly
    result_ids = set(result["id"] for result in results)
    entries = [entry_queries.by_id(id) for id in result_ids]
    # for it to be an exact match, we also need test_data to match
    matching = [e for e in entries if e.test_data == warning.test_data]

    # return latest version
    # (is this right?)
    # (what if there is a warning for an older version?)
    # matching.sort(lambda e: e.entry_version)
    if matching:
        return matching[0]


# TODO: how to make sure warning persists even on edits?
# e.g. if a new SAOLLemman is added then paths in test_data may change
# so maybe should separate: identifier, info about how to repro
# OR: one warning per test_name/entry pair
# Oh no but: we want NEW warnings to appear even if it's ignored
# (maybe take away ignored_forever or whatever)
