"""Re-fetch (cache when available) and re-parse all five schemes with cleaning."""

from ingestion.fetch import fetch_all_schemes
from ingestion.parse import parse_all_schemes


def main() -> None:
    results = fetch_all_schemes()
    ok = sum(1 for r in results if r.success)
    print(f"Fetch: {ok}/{len(results)} succeeded")

    documents = parse_all_schemes(write=True)
    print(f"Parsed and cleaned: {len(documents)} schemes")
    for doc in documents:
        managers = len(doc.sections["fund_management"].managers)
        print(
            f"  - {doc.slug}: expense_ratio ok={bool(doc.sections['expense_ratio'].text.strip())}, "
            f"managers={managers}"
        )


if __name__ == "__main__":
    main()
