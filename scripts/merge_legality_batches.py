from __future__ import annotations

import sys

from legality_batch_utils import (
    BatchValidationError,
    casefold_key,
    validate_batches,
    write_legality_dataset,
)


def main() -> int:
    try:
        result = validate_batches()
        deduped_rows = {}

        for row in result.rows:
            final_key = casefold_key(*row.final_key)
            existing = deduped_rows.get(final_key)

            if existing is None:
                deduped_rows[final_key] = row
                continue

            if existing.exact_key != row.exact_key:
                raise BatchValidationError(
                    f"Conflicting duplicate detected during merge for {row.activity!r} / {row.country!r}: "
                    f"{existing.location()} vs {row.location()}"
                )

            raise BatchValidationError(
                f"Duplicate detected during merge for {row.activity!r} / {row.country!r}: "
                f"{existing.location()} vs {row.location()}"
            )

        output_path = write_legality_dataset(list(deduped_rows.values()))
    except BatchValidationError as exc:
        print("Legality batch merge failed.")
        print(exc)
        return 1

    print(f"Merged {len(deduped_rows)} legality rows into {output_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
