'''Download a product page and extract its title and price.'''

import requests
from bs4 import BeautifulSoup

HEADERS = {'User-Agent': 'Mozilla/5.0 (price-tracker learning project)'}
TIMEOUT_SECONDS = 10

# CSS selectors for the price, tried in order. The first is for books.toscrape.com
PRICE_SELECTORS = ('p.price_color', 'span.price', '.product-price')


class PriceNotFoundError(ValueError):
    '''Raised when a price cannot be found or read.'''
    

def get_page(url: str) -> str:
    '''Return the HTML of ``url``. Raises `requests.HTTPError`` on an error status.'''
    response =  requests.get(url, headers=HEADERS, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    return response.text


def get_title(html: str) -> str:
    '''Return the text of the page's first <h1>, or 'Unknown product'.'''
    heading = BeautifulSoup(html, 'html.parser').select_one('h1')
    return heading.text.strip() if heading else 'Unknown product'


def parse_price(text: str) -> float:
    '''Convert price text such as '$1.67' or '$1,399' to a float.'''
    # keep digits and the dot only. this also drops the stray 'Â' that appears
    # when a page is decoded with the wrong charset
    cleaned = ''.join(ch for ch in text if ch.isdigit() or ch == '.')
    try:
        return float(cleaned)
    except ValueError:
        raise PriceNotFoundError(f'Could not read a price from {text!r}') from None
    

def get_price(html: str) -> float:
    '''Return the price found in ``html``.
    
    Raise PriceNotFoundError if no selector matches, for example when the
    site changed its layout or loads the price with JavaScript.
    '''
    soup = BeautifulSoup(html, 'html.parser')
    for selector in PRICE_SELECTORS:
        tag = soup.select_one(selector)
        if tag is not None:
            return parse_price(tag.text)
    raise PriceNotFoundError('Price not found: the page layout may have changed')


