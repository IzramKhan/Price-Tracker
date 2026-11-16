import sqlite3
from unittest.mock import Mock, patch

import pytest
import requests

import main
from scraper import PriceNotFoundError, get_page, get_price, get_title, parse_price
from storage import get_last_price, init_db, save_price
from tracker import (
    PriceChange,
    compare_prices,
    format_message,
    percent_change,
    should_alert,
)

URL = "https://example.com/product"


def page_with_price(price: str, title: str = "A Light in the Attic") -> str:
    return f'<html><body><h1>{title}</h1><p class="price_color">£{price}</p></body></html>'


# --- scraper -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("£51.77", 51.77), ("$1,299.00", 1299.0), ("Â£51.77", 51.77)],
)
def test_parse_price_keeps_only_the_number(text, expected):
    assert parse_price(text) == expected


@pytest.mark.parametrize("text", ["N/A", ""])
def test_parse_price_rejects_text_without_a_number(text):
    with pytest.raises(PriceNotFoundError):
        parse_price(text)


def test_get_title_reads_the_first_heading():
    assert get_title(page_with_price("10.00")) == "A Light in the Attic"


def test_get_title_falls_back_when_there_is_no_heading():
    assert get_title("<html></html>") == "Unknown product"


def test_get_price_reads_the_price():
    assert get_price(page_with_price("51.77")) == 51.77


def test_get_price_uses_a_fallback_selector():
    html = '<html><body><span class="price">$19.99</span></body></html>'
    assert get_price(html) == 19.99


def test_get_price_raises_when_no_price_is_found():
    with pytest.raises(PriceNotFoundError):
        get_price("<html><body><h1>No price here</h1></body></html>")


def test_get_page_returns_the_html():
    response = Mock(text="<html>ok</html>")

    with patch("scraper.requests.get", return_value=response) as fake_get:
        result = get_page(URL)

    assert result == "<html>ok</html>"
    assert fake_get.call_args.kwargs["timeout"] > 0
    response.raise_for_status.assert_called_once()


def test_get_page_raises_on_an_error_status():
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("404")

    with patch("scraper.requests.get", return_value=response):
        with pytest.raises(requests.HTTPError):
            get_page(URL)


# --- storage -----------------------------------------------------------------


@pytest.fixture
def conn():
    connection = init_db(":memory:")
    yield connection
    connection.close()


def test_last_price_is_none_for_an_unknown_product(conn):
    assert get_last_price(conn, URL) is None


def test_last_price_is_the_most_recent_one(conn):
    save_price(conn, URL, "Book", 51.77)
    save_price(conn, URL, "Book", 49.50)

    assert get_last_price(conn, URL) == 49.50


def test_prices_are_kept_separately_for_each_product(conn):
    save_price(conn, "https://example.com/a", "Book A", 10.0)
    save_price(conn, "https://example.com/b", "Book B", 20.0)

    assert get_last_price(conn, "https://example.com/a") == 10.0
    assert get_last_price(conn, "https://example.com/b") == 20.0


def test_a_negative_price_is_rejected_and_not_saved(conn):
    with pytest.raises(sqlite3.IntegrityError):
        save_price(conn, URL, "Book", -1.0)

    assert get_last_price(conn, URL) is None


# --- tracker -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("previous", "current", "expected"),
    [
        (None, 10.0, PriceChange.FIRST),
        (10.0, 8.0, PriceChange.DROP),
        (10.0, 12.0, PriceChange.RISE),
        (10.0, 10.0, PriceChange.SAME),
    ],
)
def test_compare_prices(previous, current, expected):
    assert compare_prices(previous, current) is expected


def test_percent_change():
    assert percent_change(50.0, 45.0) == pytest.approx(-10.0)
    assert percent_change(50.0, 55.0) == pytest.approx(10.0)


def test_percent_change_rejects_a_zero_starting_price():
    with pytest.raises(ValueError):
        percent_change(0.0, 5.0)


@pytest.mark.parametrize(
    ("change", "current", "target", "expected"),
    [
        (PriceChange.DROP, 40.0, None, True),  # any drop, no target
        (PriceChange.DROP, 40.0, 45.0, True),  # below the target
        (PriceChange.DROP, 45.0, 45.0, True),  # exactly on the target
        (PriceChange.DROP, 50.0, 45.0, False),  # dropped, but above the target
        (PriceChange.RISE, 40.0, 45.0, False),
        (PriceChange.SAME, 40.0, 45.0, False),
        (PriceChange.FIRST, 40.0, 45.0, False),
    ],
)
def test_should_alert(change, current, target, expected):
    assert should_alert(change, current, target) is expected


def test_format_message_for_each_kind_of_change():
    title = "Book"
    assert format_message(title, None, 10.0, PriceChange.FIRST) == "Book: first price recorded: 10.00"
    assert format_message(title, 10.0, 10.0, PriceChange.SAME) == "Book: no change (10.00)"
    assert format_message(title, 10.0, 12.0, PriceChange.RISE) == "Book: price rose from 10.00 to 12.00 (+20.0%)"
    assert format_message(title, 10.0, 8.0, PriceChange.DROP) == "Book: price dropped from 10.00 to 8.00 (-20.0%)"


def test_format_message_marks_an_alert():
    message = format_message("Book", 10.0, 8.0, PriceChange.DROP, alert=True)

    assert message.startswith("ALERT - ")


def test_format_message_skips_the_percentage_when_the_old_price_is_zero():
    message = format_message("Book", 0.0, 5.0, PriceChange.RISE)

    assert message == "Book: price rose from 0.00 to 5.00"


# --- main (whole program, no internet) -----------------------------------------


def run_main(monkeypatch, db_path, price, *extra_args):
    monkeypatch.setattr(main, "get_page", lambda url: page_with_price(price))
    return main.main([URL, "--db", str(db_path), *extra_args])


def test_main_tracks_prices_across_runs(monkeypatch, tmp_path, capsys):
    db = tmp_path / "prices.db"
    steps = [
        ("51.77", [], "first price recorded: 51.77"),
        ("51.77", [], "no change (51.77)"),
        ("55.00", [], "price rose from 51.77 to 55.00"),
        ("49.00", ["--target", "45"], "price dropped from 55.00 to 49.00"),
        ("44.00", ["--target", "45"], "ALERT - A Light in the Attic: price dropped from 49.00 to 44.00"),
    ]

    for price, extra, expected in steps:
        assert run_main(monkeypatch, db, price, *extra) == 0
        assert expected in capsys.readouterr().out

    connection = init_db(str(db))
    assert get_last_price(connection, URL) == 44.00
    connection.close()


def test_main_returns_1_when_the_download_fails(monkeypatch, tmp_path, capsys):
    def fail(url):
        raise requests.ConnectionError("no connection")

    monkeypatch.setattr(main, "get_page", fail)

    assert main.main([URL, "--db", str(tmp_path / "prices.db")]) == 1
    assert "could not download" in capsys.readouterr().err


def test_main_returns_1_when_the_price_is_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(main, "get_page", lambda url: "<html><h1>No price</h1></html>")

    assert main.main([URL, "--db", str(tmp_path / "prices.db")]) == 1
    assert "Price not found" in capsys.readouterr().err


def test_main_does_not_save_anything_when_the_check_fails(monkeypatch, tmp_path):
    db = tmp_path / "prices.db"
    monkeypatch.setattr(main, "get_page", lambda url: "<html></html>")

    main.main([URL, "--db", str(db)])

    assert not db.exists()


def test_main_rejects_a_negative_target(tmp_path):
    with pytest.raises(SystemExit) as error:
        main.main([URL, "--db", str(tmp_path / "prices.db"), "--target", "-5"])

    assert error.value.code == 2
    
def test_version_option_prints_the_version_and_exits(capsys):
    with pytest.raises(SystemExit) as error:
        main.main(["--version"])

    assert error.value.code == 0
    assert main.VERSION in capsys.readouterr().out
