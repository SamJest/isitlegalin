from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path


REQUIRED_LEGALITY_HEADERS = ["activity", "country", "legal_status", "notes", "topic"]
VALID_LEGAL_STATUS_VALUES = {"legal", "restricted", "illegal"}
REFERENCE_COUNTRY_HEADERS = ["country", "slug", "region"]
REFERENCE_ACTIVITY_HEADERS = ["activity", "topic"]
REFERENCE_TOPIC_REQUIRED_HEADERS = ["topic"]

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
BATCHES_DIR = DATA_DIR / "batches"
ACTIVITIES_FILE = DATA_DIR / "activities_master_list.csv"
COUNTRIES_FILE = DATA_DIR / "countries.csv"
TOPICS_FILE = DATA_DIR / "topics.csv"
LEGALITY_FILE = DATA_DIR / "legality_dataset.csv"


class BatchValidationError(Exception):
    pass


@dataclass(frozen=True)
class BatchRow:
    activity: str
    country: str
    legal_status: str
    notes: str
    topic: str
    source_path: Path
    row_number: int

    @property
    def final_key(self) -> tuple[str, str]:
        return (self.activity, self.country)

    @property
    def exact_key(self) -> tuple[str, str, str, str, str]:
        return (
            self.activity,
            self.country,
            self.legal_status,
            self.notes,
            self.topic,
        )

    def as_csv_row(self) -> list[str]:
        return [
            self.activity,
            self.country,
            self.legal_status,
            self.notes,
            self.topic,
        ]

    def location(self) -> str:
        return f"{display_path(self.source_path)}:{self.row_number}"


@dataclass(frozen=True)
class ValidationContext:
    rows: list[BatchRow]
    activities_by_name: dict[str, str]
    countries_by_name: dict[str, dict[str, str]]
    valid_topics: set[str]


def display_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def casefold_key(*values: str) -> tuple[str, ...]:
    return tuple(value.casefold() for value in values)


def format_header(headers: list[str]) -> str:
    return ",".join(headers)


def raise_for_errors(errors: list[str]) -> None:
    if errors:
        raise BatchValidationError("\n".join(errors))


def iter_batch_files() -> list[Path]:
    if not BATCHES_DIR.exists():
        return []

    return sorted(
        [path for path in BATCHES_DIR.rglob("*.csv") if path.is_file()],
        key=lambda path: display_path(path).casefold(),
    )


def read_csv_rows(path: Path, expected_headers: list[str] | None = None) -> list[tuple[int, dict[str, str]]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)

        try:
            raw_headers = next(reader)
        except StopIteration as exc:
            raise BatchValidationError(f"{display_path(path)}: file is empty") from exc

        headers = [header.strip() for header in raw_headers]

        if expected_headers is not None and headers != expected_headers:
            raise BatchValidationError(
                f"{display_path(path)}: invalid header order. Expected "
                f"{format_header(expected_headers)} but found {format_header(headers)}"
            )

        output = []

        for row_number, values in enumerate(reader, start=2):
            if not values or all(not value.strip() for value in values):
                continue

            if len(values) != len(headers):
                raise BatchValidationError(
                    f"{display_path(path)}:{row_number}: expected {len(headers)} columns but found {len(values)}"
                )

            output.append((row_number, dict(zip(headers, [value.strip() for value in values]))))

        return output


def load_reference_table(path: Path, required_headers: list[str]) -> list[dict[str, str]]:
    rows = read_csv_rows(path)
    if not rows:
        raise BatchValidationError(f"{display_path(path)}: reference dataset has no data rows")

    headers = list(rows[0][1].keys())
    missing = [header for header in required_headers if header not in headers]
    if missing:
        raise BatchValidationError(
            f"{display_path(path)}: missing required columns: {', '.join(missing)}"
        )

    return [row for _, row in rows]


def load_activities_reference() -> dict[str, str]:
    rows = load_reference_table(ACTIVITIES_FILE, REFERENCE_ACTIVITY_HEADERS)
    mapping: dict[str, str] = {}
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        activity = row["activity"].strip()
        topic = row["topic"].strip()

        if not activity or not topic:
            errors.append(
                f"{display_path(ACTIVITIES_FILE)}:{index}: activity and topic are required"
            )
            continue

        previous_topic = mapping.get(activity)
        if previous_topic and previous_topic != topic:
            errors.append(
                f"{display_path(ACTIVITIES_FILE)}:{index}: activity {activity!r} maps to both "
                f"{previous_topic!r} and {topic!r}"
            )
            continue

        mapping[activity] = topic

    raise_for_errors(errors)
    return mapping


def load_countries_reference() -> dict[str, dict[str, str]]:
    rows = load_reference_table(COUNTRIES_FILE, REFERENCE_COUNTRY_HEADERS)
    mapping: dict[str, dict[str, str]] = {}
    errors: list[str] = []

    for index, row in enumerate(rows, start=2):
        country = row["country"].strip()
        slug = row["slug"].strip()
        region = row["region"].strip()

        if not country or not slug or not region:
            errors.append(
                f"{display_path(COUNTRIES_FILE)}:{index}: country, slug, and region are required"
            )
            continue

        previous = mapping.get(country)
        current = {"slug": slug, "region": region}
        if previous and previous != current:
            errors.append(
                f"{display_path(COUNTRIES_FILE)}:{index}: duplicate country {country!r} has conflicting values"
            )
            continue

        mapping[country] = current

    raise_for_errors(errors)
    return mapping


def load_topics_reference(activities_by_name: dict[str, str]) -> set[str]:
    if TOPICS_FILE.exists():
        rows = load_reference_table(TOPICS_FILE, REFERENCE_TOPIC_REQUIRED_HEADERS)
        topics = {row["topic"].strip() for row in rows if row["topic"].strip()}
        if not topics:
            raise BatchValidationError(f"{display_path(TOPICS_FILE)}: no topic values found")
        return topics

    return set(activities_by_name.values())


def validate_batches() -> ValidationContext:
    activities_by_name = load_activities_reference()
    countries_by_name = load_countries_reference()
    valid_topics = load_topics_reference(activities_by_name)
    batch_files = iter_batch_files()

    if not batch_files:
        raise BatchValidationError("No batch CSV files found under data/batches/")

    errors: list[str] = []
    rows: list[BatchRow] = []
    exact_keys_seen: dict[tuple[str, ...], BatchRow] = {}
    final_keys_seen: dict[tuple[str, str], BatchRow] = {}

    for batch_file in batch_files:
        try:
            raw_rows = read_csv_rows(batch_file, expected_headers=REQUIRED_LEGALITY_HEADERS)
        except BatchValidationError as exc:
            errors.append(str(exc))
            continue

        file_exact_keys_seen: dict[tuple[str, ...], BatchRow] = {}
        file_final_keys_seen: dict[tuple[str, str], BatchRow] = {}

        for row_number, row in raw_rows:
            batch_row = BatchRow(
                activity=row["activity"],
                country=row["country"],
                legal_status=row["legal_status"],
                notes=row["notes"],
                topic=row["topic"],
                source_path=batch_file,
                row_number=row_number,
            )

            missing_fields = [
                field_name
                for field_name in REQUIRED_LEGALITY_HEADERS
                if not getattr(batch_row, field_name)
            ]
            if missing_fields:
                errors.append(
                    f"{batch_row.location()}: missing required values for {', '.join(missing_fields)}"
                )
                continue

            if batch_row.legal_status not in VALID_LEGAL_STATUS_VALUES:
                errors.append(
                    f"{batch_row.location()}: invalid legal_status {batch_row.legal_status!r}. "
                    f"Allowed values: legal, restricted, illegal"
                )

            expected_topic = activities_by_name.get(batch_row.activity)
            if expected_topic is None:
                errors.append(
                    f"{batch_row.location()}: unknown activity {batch_row.activity!r} in activities_master_list.csv"
                )
            elif batch_row.topic != expected_topic:
                errors.append(
                    f"{batch_row.location()}: topic {batch_row.topic!r} does not match activities_master_list.csv "
                    f"mapping for activity {batch_row.activity!r} (expected {expected_topic!r})"
                )

            if batch_row.country not in countries_by_name:
                errors.append(
                    f"{batch_row.location()}: unknown country {batch_row.country!r} in countries.csv"
                )

            if batch_row.topic not in valid_topics:
                errors.append(
                    f"{batch_row.location()}: unknown topic {batch_row.topic!r}"
                )

            exact_key = casefold_key(*batch_row.exact_key)
            final_key = casefold_key(*batch_row.final_key)

            previous_exact_in_file = file_exact_keys_seen.get(exact_key)
            if previous_exact_in_file:
                errors.append(
                    f"{batch_row.location()}: duplicate row within batch file; first seen at "
                    f"{previous_exact_in_file.location()}"
                )
            else:
                file_exact_keys_seen[exact_key] = batch_row

            previous_final_in_file = file_final_keys_seen.get(final_key)
            if previous_final_in_file:
                errors.append(
                    f"{batch_row.location()}: duplicate final key activity+country within batch file; first seen at "
                    f"{previous_final_in_file.location()}"
                )
            else:
                file_final_keys_seen[final_key] = batch_row

            previous_exact_global = exact_keys_seen.get(exact_key)
            if previous_exact_global:
                errors.append(
                    f"{batch_row.location()}: duplicate row across batch files; first seen at "
                    f"{previous_exact_global.location()}"
                )
            else:
                exact_keys_seen[exact_key] = batch_row

            previous_final_global = final_keys_seen.get(final_key)
            if previous_final_global:
                if previous_final_global.exact_key == batch_row.exact_key:
                    errors.append(
                        f"{batch_row.location()}: duplicate final key activity+country across batch files; "
                        f"same row already exists at {previous_final_global.location()}"
                    )
                else:
                    errors.append(
                        f"{batch_row.location()}: conflicting duplicate for activity+country already defined at "
                        f"{previous_final_global.location()}"
                    )
            else:
                final_keys_seen[final_key] = batch_row

            rows.append(batch_row)

    raise_for_errors(errors)
    return ValidationContext(
        rows=rows,
        activities_by_name=activities_by_name,
        countries_by_name=countries_by_name,
        valid_topics=valid_topics,
    )


def write_legality_dataset(rows: list[BatchRow]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    sorted_rows = sorted(
        rows,
        key=lambda row: casefold_key(row.topic, row.activity, row.country),
    )

    with LEGALITY_FILE.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(REQUIRED_LEGALITY_HEADERS)
        for row in sorted_rows:
            writer.writerow(row.as_csv_row())

    return LEGALITY_FILE


def load_legality_dataset() -> list[dict[str, str]]:
    if not LEGALITY_FILE.exists():
        raise BatchValidationError(
            f"{display_path(LEGALITY_FILE)} does not exist. Run merge_legality_batches.py first."
        )

    rows = read_csv_rows(LEGALITY_FILE, expected_headers=REQUIRED_LEGALITY_HEADERS)
    return [row for _, row in rows]
