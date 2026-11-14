'''Compare a new price with the previous one and report the result'''

from enum import Enum


class PriceChange(Enum):
    FIRST = 'first' # no previous price to compare with
    DROP = 'drop'
    RISE = 'rise'
    SAME = 'same'
    
    
def compare_prices(previous: float | None, current: float) -> PriceChange:
    '''Classify how ``current`` differs from ``previous``.'''
    if previous is None:
        return PriceChange.FIRST
    if current < previous:
        return PriceChange.DROP
    if current > previous:
        return PriceChange.RISE
    return PriceChange.SAME


def percent_change(previous: float, current: float) -> float:
    '''Return the change from ``previous`` to ``current`` as a percentage.'''
    if previous == 0:
        raise ValueError('Cannot calculate a percentage change from a price of 0.')
    return (current - previous) / previous * 100


def should_alert(
    change: PriceChange, current: float, target_price: float | None = None
) -> bool:
    '''Return True for a price drop.
    
    If ``target_price`` is given, the drop must also reach it (``current`` at or
    below the target).
    '''
    if change is not PriceChange.DROP:
        return False
    return target_price is None or current <= target_price


def format_message(
    title: str,
    previous: float | None,
    current: float,
    change: PriceChange,
    alert: bool = False,
) -> str:
    '''Build the one-line message describing a price check.'''
    if change is PriceChange.FIRST:
        return f'{title}: first price recorded: {current:.2f}'
    if change is PriceChange.SAME:
        return f'{title}: no change ({current:.2f})'
    
    assert previous is not None # FIRST is the only change without a previous price
    verb = 'dropped' if change is PriceChange.DROP else 'rose'
    message = f'{title}: price {verb} from {previous:.2f} to {current:.2f}'
    if previous != 0:
        message += f' ({percent_change(previous, current):+.1f}%)'
    return f'ALERT - {message}' if alert else message



def notify(
    title: str,
    previous: float | None,
    current: float,
    change: PriceChange,
    alert: bool = False,
) -> None:
    '''Print the result of a price check to the terminal.'''
    print(format_message(title, previous, current, change, alert))
