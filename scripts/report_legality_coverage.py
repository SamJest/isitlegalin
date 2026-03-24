from __future__ import annotations

import sys
from collections import defaultdict

from legality_batch_utils import (
    BatchValidationError,
    casefold_key,
    load_activities_reference,
    load_countries_reference,
    load_legality_dataset,
    load_topics_reference,
)


def format_percent(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def main() -> int:
    try:
        activities_by_name = load_activities_reference()
        countries_by_name = load_countries_reference()
        valid_topics = load_topics_reference(activities_by_name)
        legality_rows = load_legality_dataset()
    except BatchValidationError as exc:
        print("Legality coverage report failed.")
        print(exc)
        return 1

    total_countries = len(countries_by_name)
    total_activities = len(activities_by_name)
    total_rows = len(legality_rows)
    total_possible = total_countries * total_activities

    topic_activity_counts = defaultdict(int)
    for topic in activities_by_name.values():
        topic_activity_counts[topic] += 1

    per_topic_rows = defaultdict(int)
    per_country_rows = defaultdict(int)
    present_keys = set()

    for row in legality_rows:
        per_topic_rows[row["topic"]] += 1
        per_country_rows[row["country"]] += 1
        present_keys.add(casefold_key(row["activity"], row["country"]))

    missing_combinations = []
    for activity, topic in sorted(
        activities_by_name.items(),
        key=lambda item: (item[1].casefold(), item[0].casefold()),
    ):
        for country in sorted(countries_by_name, key=str.casefold):
            final_key = casefold_key(activity, country)
            if final_key not in present_keys:
                missing_combinations.append((topic, activity, country))

    print("Legality coverage report")
    print(f"Total countries: {total_countries}")
    print(f"Total activities: {total_activities}")
    print(f"Total legality rows: {total_rows}")
    print(f"Expected activity-country combinations: {total_possible}")
    print(f"Missing activity-country combinations: {len(missing_combinations)}")
    print("")
    print("Per-topic coverage")

    for topic in sorted(valid_topics, key=str.casefold):
        possible_rows = topic_activity_counts[topic] * total_countries
        actual_rows = per_topic_rows.get(topic, 0)
        print(
            f"- {topic}: {actual_rows}/{possible_rows} ({format_percent(actual_rows, possible_rows)})"
        )

    print("")
    print("Per-country coverage")

    for country in sorted(countries_by_name, key=str.casefold):
        actual_rows = per_country_rows.get(country, 0)
        print(
            f"- {country}: {actual_rows}/{total_activities} "
            f"({format_percent(actual_rows, total_activities)})"
        )

    if missing_combinations:
        print("")
        print("Next missing combinations")
        for topic, activity, country in missing_combinations[:25]:
            print(f"- {topic} | {activity} | {country}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
