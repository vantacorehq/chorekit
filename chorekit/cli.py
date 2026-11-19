"""Command line interface: python -m chorekit <command> ..."""

import argparse
import sys
from pathlib import Path

import requests

from chorekit import __version__
from chorekit.rates import convert, fetch_exchange_rates, filter_rates, save_rates
from chorekit.report import RENDERERS, build_report
from chorekit.sorter import sort_folder, undo_last_sort


def _folder_or_none(value: str):
    folder = Path(value).expanduser().resolve()
    if not folder.exists() or not folder.is_dir():
        print(f"Folder not found: {folder}", file=sys.stderr)
        return None
    return folder


def cmd_sort(args) -> int:
    folder = _folder_or_none(args.folder)
    if folder is None:
        return 1

    print(f"Sorting files in: {folder}\n")
    stats, _ = sort_folder(folder, dry_run=args.dry_run, recursive=args.recursive, by=args.by)

    print("\nSummary:")
    if not stats:
        print("  No files to sort (or everything is already sorted).")
    for name, count in sorted(stats.items()):
        print(f"  {name}: {count} file(s)")
    if not args.dry_run and stats:
        print("\nUndo with: python -m chorekit undo", args.folder)
    return 0


def cmd_undo(args) -> int:
    folder = _folder_or_none(args.folder)
    if folder is None:
        return 1
    try:
        restored, skipped = undo_last_sort(folder)
    except FileNotFoundError as e:
        print(e, file=sys.stderr)
        return 1
    print(f"\nRestored {restored} file(s), skipped {skipped}.")
    return 0 if skipped == 0 else 1


def cmd_report(args) -> int:
    folder = _folder_or_none(args.folder)
    if folder is None:
        return 1
    report = build_report(folder, recursive=args.recursive, top=args.top)
    text = RENDERERS[args.format](report)
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
        print(f"Report saved to: {args.output}")
    else:
        print(text, end="")
    return 0


def cmd_rates(args) -> int:
    if args.convert is not None and not args.to:
        print("--convert needs --to, for example: --convert 100 --to EUR", file=sys.stderr)
        return 1

    print(f"Fetching exchange rates relative to {args.base.upper()}...")
    try:
        data = fetch_exchange_rates(args.base, retries=args.retries, backoff=args.backoff)
        if args.symbols:
            data = filter_rates(data, args.symbols.split(","))
        converted = convert(args.convert, data, args.to) if args.convert is not None else None
    except requests.RequestException as e:
        print(f"API request error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Data error: {e}", file=sys.stderr)
        return 1

    output = args.output or f"exchange_rates.{args.format}"
    save_rates(data, output, args.format)
    print(f"Done! Got {len(data.get('rates', {}))} exchange rates, saved to: {output}")
    if converted is not None:
        print(f"{args.convert:g} {args.base.upper()} = {converted:.2f} {args.to.upper()}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="chorekit", description="Small command line tools for everyday chores.")
    parser.add_argument("--version", action="version", version=f"chorekit {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sort", help="Sort the files of a folder into subfolders")
    p.add_argument("folder", help="Path to the folder to sort")
    p.add_argument("--dry-run", action="store_true", help="Only show the plan, do not move any files")
    p.add_argument("--recursive", action="store_true", help="Also sort files inside subfolders")
    p.add_argument("--by", choices=["type", "month"], default="type",
                   help="Sort by file type (default) or by modification month")
    p.set_defaults(func=cmd_sort)

    p = sub.add_parser("undo", help="Undo the last sort of a folder")
    p.add_argument("folder", help="Path to the folder that was sorted")
    p.set_defaults(func=cmd_undo)

    p = sub.add_parser("report", help="Report files and size per category")
    p.add_argument("folder", help="Path to the folder to analyze")
    p.add_argument("--recursive", action="store_true", help="Include subfolders")
    p.add_argument("--top", type=int, default=5, help="How many largest files to list (default 5)")
    p.add_argument("--format", choices=sorted(RENDERERS), default="md", help="md (default), csv or json")
    p.add_argument("--output", help="Write the report to this file instead of printing it")
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("rates", help="Download exchange rates")
    p.add_argument("--base", default="USD", help="Base currency, e.g. USD, EUR, UAH (default USD)")
    p.add_argument("--symbols", help="Keep only these currencies, e.g. EUR,GBP,PLN")
    p.add_argument("--convert", type=float, help="Amount of the base currency to convert")
    p.add_argument("--to", help="Target currency for --convert")
    p.add_argument("--format", choices=["json", "csv"], default="json", help="Output format (default json)")
    p.add_argument("--output", help="Output file (default exchange_rates.json or exchange_rates.csv)")
    p.add_argument("--retries", type=int, default=3, help="Retries on network errors (default 3)")
    p.add_argument("--backoff", type=float, default=1.0, help="First retry wait in seconds, doubles each time (default 1.0)")
    p.set_defaults(func=cmd_rates)

    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)
