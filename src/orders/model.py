from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from fractions import Fraction


class Side(Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(Enum):
    NEW = "new"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELED = "canceled"


TERMINAL = {OrderStatus.FILLED, OrderStatus.CANCELED}


@dataclass(frozen=True)
class Fill:
    qty: Decimal
    price: Decimal


@dataclass
class Order:
    id: str
    side: Side
    qty: Decimal
    limit_price: Decimal
    status: OrderStatus = OrderStatus.NEW
    fills: list[Fill] = field(default_factory=list)

    @property
    def filled_qty(self) -> Decimal:
        return sum((f.qty for f in self.fills), Decimal(0))

    @property
    def remaining_qty(self) -> Decimal:
        return self.qty - self.filled_qty

    @property
    def average_fill_price(self) -> Decimal | None:
        """Volume-weighted average price of the fills, None if there are no fills.

        Reported to 6 decimal places, rounding half to even.
        """
        if not self.fills:
            return None
        # Fractions are exact and ignore the caller's decimal context, so we round only once.
        notional = sum(Fraction(f.qty) * Fraction(f.price) for f in self.fills)
        average = notional / sum(Fraction(f.qty) for f in self.fills)
        millionths = round(average * 10**6)  # round() on a Fraction is half to even
        return Decimal(f"{millionths}E-6")  # building from a string is exact
