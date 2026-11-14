"""Command-line entry point: check a product's price and report any change."""

import argparse
import contextlib
import sys

import requests

from scraper import PriceNotFoundError, get_page, get_price, get_title
from storage import DEFAULT_DB_PATH, get_last_price, init_db, save_price
from tracker import compare_prices, notify, should_alert


def non_negative_float(value: str) -> float:
    number = float(value)
    if number < 0:
        raise argparse.ArgumentTypeError("must be 0 or greater")
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check a product's price and compare it with the last check."
    )
    parser.add_argument("url", help="URL of the product page")
    parser.add_argument(
        "--target",
        type=non_negative_float,
        help="only alert when the price drops to this value or lower",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB_PATH,
        help="path to the SQLite database (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        html = get_page(args.url)
        title = get_title(html)
        current = get_price(html)
    except requests.RequestException as error:
        print(f"Error: could not download the page: {error}", file=sys.stderr)
        return 1
    except PriceNotFoundError as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    with contextlib.closing(init_db(args.db)) as conn:
        previous = get_last_price(conn, args.url)  # must be read before saving
        save_price(conn, args.url, title, current)

    change = compare_prices(previous, current)
    alert = should_alert(change, current, args.target)
    notify(title, previous, current, change, alert)
    return 0


if __name__ == "__main__":
    sys.exit(main())