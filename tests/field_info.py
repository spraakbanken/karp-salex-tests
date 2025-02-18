from karp.foundation import json
from collections import defaultdict, Counter
from dataclasses import dataclass
from utils.testing import TestWarning

@dataclass
class Statistics:
    field: str
    present: int
    total: int

    @property
    def missing(self):
        return self.total - self.present

    @property
    def missing_freq(self):
        return self.missing / self.total

    @property
    def present_freq(self):
        return self.present / self.total

def resource_statistics(resource_config, entries):
    present_counts = Counter()
    total_counts = Counter()

    for entry in entries:
        count_frequency([], resource_config.entry_field_config(), entry.entry, present_counts, total_counts)

    for field, total_count in total_counts.items():
        present_count = present_counts[field]

        if field != "":
            yield Statistics(field, present_count, total_count)


def count_frequency(path, field_config, data, present_counts, total_counts):
    if field_config.virtual:
        return

    field_name = ".".join(path)

    if field_config.collection:
        values = data
    else:
        values = [data]

    for value in values:
        total_counts[field_name] += 1
        present_counts[field_name] += 1

        if field_config.type == "object":
            for sub_name, sub_config in field_config.fields.items():
                if sub_name in value:
                    count_frequency(
                        path + [sub_name],
                        sub_config,
                        value[sub_name],
                        present_counts,
                        total_counts,
                    )
                elif not sub_config.virtual:
                    total_counts[".".join(path + [sub_name])] += 1

            # Find extra fields not declared in the resource config
            for sub_name in value:
                if sub_name not in field_config.fields:
                    total_counts[".".join(path + [sub_name])] += 1
                    present_counts[".".join(path + [sub_name])] += 1


@dataclass(frozen=True)
class FieldStatistics(TestWarning):
    _category: str
    statistics: Statistics

    def category(self):
        return self._category

    def to_dict(self):
        frequency = f"{self.statistics.present_freq*100:.2f}% ({self.statistics.present})"
        return {
            "Fält": self.statistics.field,
            "Frekvens": frequency
        }

def test_field_info(resource_config, entries):
    statistics = list(resource_statistics(resource_config, entries))
    always_present = [s for s in statistics if s.missing_freq == 0]
    usually_present = [s for s in statistics if 0 < s.missing_freq <= 0.05]
    usually_absent = [s for s in statistics if s.present_freq <= 0.05]

    for s in always_present:
        yield FieldStatistics("Always present", s)

    for s in usually_present:
        yield FieldStatistics("Usually present", s)

    for s in usually_absent:
        yield FieldStatistics("Usually absent", s)

    resource_config_fields = set(resource_config.nested_fields())
    for s in statistics:
        if s.field not in resource_config_fields:
            yield FieldStatistics("Extra fields", s)
