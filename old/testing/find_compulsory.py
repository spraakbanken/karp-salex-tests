# guess which fields might be references

from karp.foundation import json
from collections import defaultdict, Counter
from dataclasses import dataclass
import pickle

# a field might be compulsory if it exists >= 95% of the time


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
                else:
                    total_counts[".".join(path + [sub_name])] += 1


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


def guess_compulsory(resource_config, entries):
    present_counts = Counter()
    total_counts = Counter()

    for entry in entries:
        count_frequency([], resource_config.entry_field_config(), entry.entry, present_counts, total_counts)

    for field, total_count in total_counts.items():
        present_count = present_counts[field]

        yield Statistics(field, present_count, total_count)


resource_config = resource_queries.by_resource_id("salex").config
# with open("../entries.pickle", "rb") as file:
#    entries = pickle.load(file)
entries = list(entry_queries.all_entries("salex", expand_plugins=False))

statistics = list(guess_compulsory(resource_config, entries))

always_present = [stat for stat in statistics if stat.missing_freq == 0]
usually_present = [stat for stat in statistics if 0 < stat.missing_freq <= 0.05]
usually_missing = [stat for stat in statistics if 0 < stat.present_freq <= 0.05]

print("Always present fields:")
for stat in sorted(always_present, key=lambda stat: stat.field):
    print(stat.field)
print()

print("Fields missing <=5% of the time:")
for stat in sorted(usually_present, key=lambda stat: (stat.missing_freq, stat.field)):
    print(f"{stat.field}: missing {stat.missing} times out of {stat.total} ({stat.missing_freq*100}%)")
print()

print("Fields present <=5% of the time:")
for stat in sorted(usually_missing, key=lambda stat: (stat.present_freq, stat.field)):
    print(f"{stat.field}: present {stat.present} times out of {stat.total} ({stat.present_freq*100}%)")

exit()
