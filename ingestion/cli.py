import argparse
import sys

from api.config import settings
from ingestion.pipeline import ingest_file


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest documents into pgvector")
    subparsers = parser.add_subparsers(dest="command", required=True)

    ingest_parser = subparsers.add_parser("ingest", help="Ingest a markdown/text file")
    ingest_parser.add_argument("path", help="Path to document")
    ingest_parser.add_argument(
        "--roles",
        nargs="+",
        default=["support", "admin"],
        help="Allowed roles stored in chunk metadata",
    )

    args = parser.parse_args(argv)

    if args.command == "ingest":
        result = ingest_file(args.path, allowed_roles=args.roles, settings=settings)
        print(f"Ingested {result.chunk_count} chunks from {result.source}")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
