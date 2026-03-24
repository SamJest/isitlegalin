from __future__ import annotations

import sys

from legality_batch_utils import BatchValidationError, validate_batches


def main() -> int:
    try:
        result = validate_batches()
    except BatchValidationError as exc:
        print("Legality batch validation failed.")
        print(exc)
        return 1

    print(
        f"Validated {len(result.rows)} legality rows across {len(result.countries_by_name)} countries, "
        f"{len(result.activities_by_name)} activities, and {len(result.valid_topics)} topics."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
