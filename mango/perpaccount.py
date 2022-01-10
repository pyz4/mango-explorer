# # ⚠ Warning
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT
# LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# [🥭 Mango Markets](https://mango.markets/) support is available at:
#   [Docs](https://docs.mango.markets/)
#   [Discord](https://discord.gg/67jySBhxrg)
#   [Twitter](https://twitter.com/mangomarkets)
#   [Github](https://github.com/blockworks-foundation)
#   [Email](mailto:hello@blockworks.foundation)

import typing

from decimal import Decimal

from .cache import PerpMarketCache
from .instrumentvalue import InstrumentValue
from .lotsizeconverter import LotSizeConverter
from .perpopenorders import PerpOpenOrders
from .token import Instrument, Token


# # 🥭 PerpAccount class
#
# Perp accounts aren't directly addressable. They exist as a sub-object of a full Mango `Account` object.
#
class PerpAccount:
    def __init__(self, base_position: Decimal, quote_position: Decimal, long_settled_funding: Decimal,
                 short_settled_funding: Decimal, bids_quantity: Decimal, asks_quantity: Decimal,
                 taker_base: Decimal, taker_quote: Decimal, mngo_accrued: InstrumentValue,
                 open_orders: PerpOpenOrders, lot_size_converter: LotSizeConverter,
                 base_token_value: InstrumentValue, quote_position_raw: Decimal) -> None:
        self.base_position: Decimal = base_position
        self.quote_position: Decimal = quote_position
        self.long_settled_funding: Decimal = long_settled_funding
        self.short_settled_funding: Decimal = short_settled_funding
        self.bids_quantity: Decimal = bids_quantity
        self.asks_quantity: Decimal = asks_quantity
        self.taker_base: Decimal = taker_base
        self.taker_quote: Decimal = taker_quote
        self.mngo_accrued: InstrumentValue = mngo_accrued
        self.open_orders: PerpOpenOrders = open_orders
        self.lot_size_converter: LotSizeConverter = lot_size_converter
        self.base_token_value: InstrumentValue = base_token_value
        self.quote_position_raw: Decimal = quote_position_raw

    @staticmethod
    def from_layout(layout: typing.Any, base_token: Instrument, quote_token: Token, open_orders: PerpOpenOrders, lot_size_converter: LotSizeConverter, mngo_token: Token) -> "PerpAccount":
        base_position: Decimal = layout.base_position
        quote_position: Decimal = layout.quote_position
        long_settled_funding: Decimal = layout.long_settled_funding
        short_settled_funding: Decimal = layout.short_settled_funding
        bids_quantity: Decimal = layout.bids_quantity
        asks_quantity: Decimal = layout.asks_quantity
        taker_base: Decimal = layout.taker_base
        taker_quote: Decimal = layout.taker_quote
        mngo_accrued_raw: Decimal = layout.mngo_accrued
        mngo_accrued: InstrumentValue = InstrumentValue(mngo_token, mngo_token.shift_to_decimals(mngo_accrued_raw))

        base_position_raw = (base_position + taker_base) * lot_size_converter.base_lot_size
        base_token_value: InstrumentValue = InstrumentValue(base_token, base_token.shift_to_decimals(base_position_raw))

        quote_position_raw: Decimal = quote_token.shift_to_decimals(quote_position)

        return PerpAccount(base_position, quote_position, long_settled_funding, short_settled_funding,
                           bids_quantity, asks_quantity, taker_base, taker_quote, mngo_accrued, open_orders,
                           lot_size_converter, base_token_value, quote_position_raw)

    @property
    def empty(self) -> bool:
        if self.base_position == Decimal(0) and self.quote_position == Decimal(0) and self.long_settled_funding == Decimal(0) and self.short_settled_funding == Decimal(0) and self.mngo_accrued.value == Decimal(0) and self.open_orders.empty:
            return True
        return False

    def unsettled_funding(self, perp_market_cache: PerpMarketCache) -> Decimal:
        base_position: Decimal = self.base_position
        unsettled: Decimal
        if base_position < 0:
            unsettled = base_position * (perp_market_cache.short_funding - self.short_settled_funding)
        else:
            unsettled = base_position * (perp_market_cache.long_funding - self.long_settled_funding)
        return - self.lot_size_converter.quote.shift_to_decimals(unsettled)

    def asset_value(self, perp_market_cache: PerpMarketCache, price: Decimal) -> Decimal:
        base_position: Decimal = self.lot_size_converter.adjust_to_quote_decimals(self.base_position)
        value: Decimal = Decimal(0)
        if base_position > 0:
            value = base_position * self.lot_size_converter.base_lot_size * price
            value = self.lot_size_converter.quote.shift_to_decimals(value)

        quote_position: Decimal = self.lot_size_converter.quote.shift_to_decimals(self.quote_position)
        quote_position += self.unsettled_funding(perp_market_cache)
        if quote_position > 0:
            value += quote_position

        return value

    def liability_value(self, perp_market_cache: PerpMarketCache, price: Decimal) -> Decimal:
        base_position: Decimal = self.lot_size_converter.adjust_to_quote_decimals(self.base_position)
        value: Decimal = Decimal(0)
        if base_position < 0:
            value = base_position * self.lot_size_converter.base_lot_size * price
            value = self.lot_size_converter.quote.shift_to_decimals(value)

        quote_position: Decimal = self.lot_size_converter.quote.shift_to_decimals(self.quote_position)
        quote_position += self.unsettled_funding(perp_market_cache)
        if quote_position < 0:
            value += quote_position

        return value

    def current_value(self, perp_market_cache: PerpMarketCache, price: Decimal) -> Decimal:
        base_position: Decimal = self.lot_size_converter.adjust_to_quote_decimals(self.base_position)
        value: Decimal = base_position * self.lot_size_converter.base_lot_size * price

        quote_position: Decimal = self.lot_size_converter.quote.shift_to_decimals(self.quote_position)
        quote_position += self.unsettled_funding(perp_market_cache)

        value += quote_position

        return self.lot_size_converter.quote.shift_to_decimals(value)

    def __str__(self) -> str:
        if self.empty:
            return "« PerpAccount (empty) »"
        open_orders = f"{self.open_orders}".replace("\n", "\n        ")
        return f"""« PerpAccount
    Base Position: {self.base_token_value}
    Quote Position: {self.quote_position}
    Long Settled Funding: {self.long_settled_funding}
    Short Settled Funding: {self.short_settled_funding}
    Bids Quantity: {self.bids_quantity}
    Asks Quantity: {self.asks_quantity}
    Taker Base: {self.taker_base}
    Taker Quote: {self.taker_quote}
    MNGO Accrued: {self.mngo_accrued}
    OpenOrders:
        {open_orders}
»"""
