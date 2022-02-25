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


import logging
import typing

from decimal import Decimal
from solana.publickey import PublicKey

from .account import Account
from .group import Group
from .inventory import Inventory
from .markets import Market
from .oracle import Price
from .orders import Order, OrderBook
from .placedorder import PlacedOrdersContainer
from .watcher import Watcher


# # 🥭 EventQueue protocol
#
# The `EventQueue` protocol just says the object has a property `accounts_to_crank` that returns a `Sequence` of `PublicKey`s.
#
# This is to share the interface between a `SerumEventQueue` and a `PerpEventQueue` for cranking, when the
# underlying objects are really quite different.
#
class EventQueue(typing.Protocol):
    @property
    def accounts_to_crank(self) -> typing.Sequence[PublicKey]:
        raise NotImplementedError(
            "EventQueue.accounts_to_crank is not implemented on the Protocol."
        )


class NullEventQueue:
    @property
    def accounts_to_crank(self) -> typing.Sequence[PublicKey]:
        return []


# # 🥭 ModelState class
#
# Provides simple access to the latest state of market and account data.
#
class ModelState:
    def __init__(
        self,
        order_owner: PublicKey,
        market: Market,
        group_watcher: Watcher[Group],
        account_watcher: Watcher[Account],
        price_watcher: Watcher[Price],
        placed_orders_container_watcher: Watcher[PlacedOrdersContainer],
        inventory_watcher: Watcher[Inventory],
        orderbook: Watcher[OrderBook],
        event_queue: Watcher[EventQueue],
    ) -> None:
        self._logger: logging.Logger = logging.getLogger(self.__class__.__name__)
        self.order_owner: PublicKey = order_owner
        self.market: Market = market
        self.group_watcher: Watcher[Group] = group_watcher
        self.account_watcher: Watcher[Account] = account_watcher
        self.price_watcher: Watcher[Price] = price_watcher
        self.placed_orders_container_watcher: Watcher[
            PlacedOrdersContainer
        ] = placed_orders_container_watcher
        self.inventory_watcher: Watcher[Inventory] = inventory_watcher
        self.orderbook_watcher: Watcher[OrderBook] = orderbook
        self.event_queue_watcher: Watcher[EventQueue] = event_queue

        self.not_quoting: bool = False
        self.state: typing.Dict[str, typing.Any] = {}

    @property
    def group(self) -> Group:
        return self.group_watcher.latest

    @property
    def account(self) -> Account:
        return self.account_watcher.latest

    @property
    def price(self) -> Price:
        return self.price_watcher.latest

    @property
    def placed_orders_container(self) -> PlacedOrdersContainer:
        return self.placed_orders_container_watcher.latest

    @property
    def inventory(self) -> Inventory:
        return self.inventory_watcher.latest

    @property
    def orderbook(self) -> OrderBook:
        return self.orderbook_watcher.latest

    @property
    def bids(self) -> typing.Sequence[Order]:
        return self.orderbook.bids

    @property
    def asks(self) -> typing.Sequence[Order]:
        return self.orderbook.asks

    # The top bid is the highest price someone is willing to pay to BUY
    @property
    def top_bid(self) -> typing.Optional[Order]:
        return self.orderbook.top_bid

    # The top ask is the lowest price someone is willing to pay to SELL
    @property
    def top_ask(self) -> typing.Optional[Order]:
        return self.orderbook.top_ask

    @property
    def spread(self) -> Decimal:
        return self.orderbook.spread

    @property
    def accounts_to_crank(self) -> typing.Sequence[PublicKey]:
        return self.event_queue_watcher.latest.accounts_to_crank

    def current_orders(self) -> typing.Sequence[Order]:
        return self.orderbook.all_orders_for_owner(
            self.order_owner, include_expired=True
        )

    def __str__(self) -> str:
        return f"""« ModelState for market '{self.market.symbol}'
    Group: {self.group_watcher.latest.address}
    Account: {self.account_watcher.latest.address}
    Price: {self.price_watcher.latest}
    Inventory: {self.inventory_watcher.latest}
    Existing Order Count: {len(self.placed_orders_container_watcher.latest.placed_orders)}
    Bid Count: {len(self.bids)}
    Ask Count: {len(self.asks)}
»"""

    def __repr__(self) -> str:
        return f"{self}"
