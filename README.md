# Price Tracker

A Python command-line tool that checks a product's price, compares it with the previous check and saves every check in a local database.

## Version 1

Features:

- Downloads a product page and reads its title and price
- Compares the price with the previous check (first reading, no change, rise or drop)
- Shows the percentage change in the terminal
- Optional target price: alerts only when a drop reaches the target
- Saves every check in a local SQLite database
- Clear error messages when the page cannot be downloaded or has no price
- Includes tests that run without internet

## How it works

`main.py` connects three modules and runs them in order:

1. `scraper.py` downloads the page and reads the title and price
2. `storage.py` reads the last saved price, then saves the new one
3. `tracker.py` compares the two prices, decides whether to alert and prints the result

## How to run

Requires Python 3.10 or newer.

```
pip install -r requirements.txt
python main.py <product_url>
python main.py <product_url> --target 45
```

Each run is one check. Run it again later to compare with the last saved price.

Options:

- `--target`: only alert when the price drops to this value or lower
- `--db`: path to the SQLite database (default: `prices.db`)
- `--version`: show the version and exit

## Help

To see all arguments, run:

```
python main.py --help
```

## How to run the tests

```
pip install pytest
python -m pytest
```

## Notes

- Built and tested against books.toscrape.com, a practice site made for scraping. Check a website's terms and access rules before tracking its prices.
- It only works for pages that include the price in the HTML they send. Pages that load prices with JavaScript are not supported.
- The price selectors are listed at the top of `scraper.py`. Add your own to track other sites.
- Prices are stored as plain numbers. The currency is not tracked.

## Coming in version 2

- Email alerts
- A list of products to track
- Scheduled runs
- Price history charts
