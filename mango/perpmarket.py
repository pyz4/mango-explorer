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


import rx.operators
import typing

from dataclasses import dataclass
from datetime import datetime
from dateutil import parser
from decimal import Decimal
from solana.publickey import PublicKey

from .account import Account
from .accountinfo import AccountInfo
from .combinableinstructions import CombinableInstructions
from .constants import SYSTEM_PROGRAM_ADDRESS
from .context import Context
from .group import Group
from .instructions import (
    build_cancel_perp_order_instructions,
    build_mango_consume_events_instructions,
    build_cancel_all_perp_orders_instructions,
    build_place_perp_order_instructions,
    build_redeem_accrued_mango_instructions,
)
from .loadedmarket import LoadedMarket
from .lotsizeconverter import LotSizeConverter, RaisingLotSizeConverter
from .markets import InventorySource, MarketType, Market
from .marketoperations import MarketInstructionBuilder, MarketOperations
from .observables import Disposable
from .orderbookside import PerpOrderBookSide
from .orders import Order, OrderBook
from .perpeventqueue import (
    PerpEvent,
    PerpEventQueue,
    PerpFillEvent,
    UnseenPerpEventChangesTracker,
)
from .perpmarketdetails import PerpMarketDetails
from .publickey import encode_public_key_for_sorting
from .tokens import Instrument, Token
from .tokenbank import TokenBank
from .wallet import Wallet
from .websocketsubscription import (
    IndividualWebSocketSubscriptionManager,
    WebSocketAccountSubscription,
)


# # 🥭 FundingRate class
#
# A simple way to package details of a funding rate in a single object.
#
@dataclass
class FundingRate:
    symbol: str
    rate: Decimal
    oracle_price: Decimal
    open_interest: Decimal
    from_: datetime
    to: datetime

    @staticmethod
    def from_stats_data(
        symbol: str,
        lot_size_converter: LotSizeConverter,
        oldest_stats: typing.Dict[str, typing.Any],
        newest_stats: typing.Dict[str, typing.Any],
    ) -> "FundingRate":
        oldest_short_funding = Decimal(oldest_stats["shortFunding"])
        oldest_long_funding = Decimal(oldest_stats["longFunding"])
        oldest_oracle_price = Decimal(oldest_stats["baseOraclePrice"])
        from_timestamp = parser.parse(oldest_stats["time"]).replace(microsecond=0)

        newest_short_funding = Decimal(newest_stats["shortFunding"])
        newest_long_funding = Decimal(newest_stats["longFunding"])
        newest_oracle_price = Decimal(newest_stats["baseOraclePrice"])
        to_timestamp = parser.parse(newest_stats["time"]).replace(microsecond=0)
        raw_open_interest = Decimal(newest_stats["openInterest"])
        open_interest = (
            lot_size_converter.base_size_lots_to_number(raw_open_interest) / 2
        )

        average_oracle_price = (oldest_oracle_price + newest_oracle_price) / 2
        average_oracle_price = newest_oracle_price

        start_funding = (oldest_long_funding + oldest_short_funding) / 2
        end_funding = (newest_long_funding + newest_short_funding) / 2
        funding_difference = end_funding - start_funding

        funding_in_quote_decimals = lot_size_converter.quote.shift_to_decimals(
            funding_difference
        )

        base_price_in_base_lots = average_oracle_price * lot_size_converter.lot_size
        funding_rate = funding_in_quote_decimals / base_price_in_base_lots
        return FundingRate(
            symbol=symbol,
            rate=funding_rate,
            oracle_price=average_oracle_price,
            open_interest=open_interest,
            from_=from_timestamp,
            to=to_timestamp,
        )

    def __str__(self) -> str:
        return f"« FundingRate {self.symbol} {self.rate:,.8%}, open interest: {self.open_interest:,.8f} from: {self.from_} to {self.to} »"

    def __repr__(self) -> str:
        return f"{self}"


# # 🥭 PerpMarket class
#
# This class encapsulates our knowledge of a Mango perps market.
#
class PerpMarket(LoadedMarket):
    def __init__(
        self,
        mango_program_address: PublicKey,
        address: PublicKey,
        base: Instrument,
        quote: Token,
        underlying_perp_market: PerpMarketDetails,
    ) -> None:
        super().__init__(
            MarketType.PERP,
            mango_program_address,
            address,
            InventorySource.ACCOUNT,
            base,
            quote,
            RaisingLotSizeConverter(),
        )
        self.underlying_perp_market: PerpMarketDetails = underlying_perp_market
        self.lot_size_converter: LotSizeConverter = LotSizeConverter(
            base,
            underlying_perp_market.base_lot_size,
            quote,
            underlying_perp_market.quote_lot_size,
        )

    @staticmethod
    def isa(market: Market) -> bool:
        return market.type == MarketType.PERP

    @staticmethod
    def ensure(market: Market) -> "PerpMarket":
        if not PerpMarket.isa(market):
            raise Exception(f"Market for {market.symbol} is not a Perp market")
        return typing.cast(PerpMarket, market)

    @property
    def symbol(self) -> str:
        return f"{self.base.symbol}-PERP"

    @property
    def group(self) -> Group:
        return self.underlying_perp_market.group

    @property
    def bids_address(self) -> PublicKey:
        return self.underlying_perp_market.bids

    @property
    def asks_address(self) -> PublicKey:
        return self.underlying_perp_market.asks

    @property
    def event_queue_address(self) -> PublicKey:
        return self.underlying_perp_market.event_queue

    def parse_account_info_to_orders(
        self, account_info: AccountInfo
    ) -> typing.Sequence[Order]:
        side: PerpOrderBookSide = PerpOrderBookSide.parse(
            account_info, self.underlying_perp_market
        )
        return side.orders()

    def fetch_funding(self, context: Context) -> FundingRate:
        stats = context.fetch_stats(
            f"perp/funding_rate?mangoGroup={self.group.name}&market={self.symbol}"
        )
        newest_stats = stats[0]
        oldest_stats = stats[-1]

        return FundingRate.from_stats_data(
            self.symbol, self.lot_size_converter, oldest_stats, newest_stats
        )

    def unprocessed_events(self, context: Context) -> typing.Sequence[PerpEvent]:
        event_queue: PerpEventQueue = PerpEventQueue.load(
            context, self.event_queue_address, self.lot_size_converter
        )
        return event_queue.unprocessed_events

    def on_fill(
        self, context: Context, handler: typing.Callable[[PerpFillEvent], None]
    ) -> Disposable:
        def _fill_filter(item: PerpEvent) -> None:
            if isinstance(item, PerpFillEvent):
                handler(item)

        return self.on_event(context, _fill_filter)

    def on_event(
        self, context: Context, handler: typing.Callable[[PerpEvent], None]
    ) -> Disposable:
        disposer = Disposable()
        initial: PerpEventQueue = PerpEventQueue.load(
            context, self.event_queue_address, self.lot_size_converter
        )

        splitter: UnseenPerpEventChangesTracker = UnseenPerpEventChangesTracker(initial)
        event_queue_subscription = WebSocketAccountSubscription(
            context,
            self.event_queue_address,
            lambda account_info: PerpEventQueue.parse(
                account_info, self.lot_size_converter
            ),
        )
        disposer.add_disposable(event_queue_subscription)

        manager = IndividualWebSocketSubscriptionManager(context)
        disposer.add_disposable(manager)
        manager.add(event_queue_subscription)

        publisher = event_queue_subscription.publisher.pipe(
            rx.operators.flat_map(splitter.unseen)
        )

        individual_event_subscription = publisher.subscribe(on_next=handler)
        disposer.add_disposable(individual_event_subscription)

        manager.open()

        return disposer

    def __str__(self) -> str:
        underlying: str = f"{self.underlying_perp_market}".replace("\n", "\n    ")
        return f"""« PerpMarket {self.symbol} {self.address} [{self.program_address}]
    {underlying}
»"""


# # 🥭 PerpMarketInstructionBuilder
#
# This file deals with building instructions for Perp markets.
#
# As a matter of policy for all InstructionBuidlers, construction and build_* methods should all work with
# existing data, requiring no fetches from Solana or other sources. All necessary data should all be loaded
# on initial setup in the `load()` method.
#
class PerpMarketInstructionBuilder(MarketInstructionBuilder):
    def __init__(
        self,
        context: Context,
        wallet: Wallet,
        perp_market: PerpMarket,
        group: Group,
        account: Account,
    ) -> None:
        super().__init__()
        self.context: Context = context
        self.wallet: Wallet = wallet
        self.perp_market: PerpMarket = perp_market
        self.group: Group = group
        self.account: Account = account
        self.mngo_token_bank: TokenBank = self.group.liquidity_incentive_token_bank

    @staticmethod
    def load(
        context: Context,
        wallet: Wallet,
        perp_market: PerpMarket,
        group: Group,
        account: Account,
    ) -> "PerpMarketInstructionBuilder":
        return PerpMarketInstructionBuilder(
            context, wallet, perp_market, group, account
        )

    def build_cancel_order_instructions(
        self, order: Order, ok_if_missing: bool = False
    ) -> CombinableInstructions:
        if self.perp_market.underlying_perp_market is None:
            raise Exception(
                f"PerpMarket {self.perp_market.symbol} has not been loaded."
            )
        return build_cancel_perp_order_instructions(
            self.context,
            self.wallet,
            self.account,
            self.perp_market.underlying_perp_market,
            order,
            ok_if_missing,
        )

    def build_place_order_instructions(self, order: Order) -> CombinableInstructions:
        if self.perp_market.underlying_perp_market is None:
            raise Exception(
                f"PerpMarket {self.perp_market.symbol} has not been loaded."
            )
        return build_place_perp_order_instructions(
            self.context,
            self.wallet,
            self.perp_market.underlying_perp_market.group,
            self.account,
            self.perp_market.underlying_perp_market,
            order.price,
            order.quantity,
            order.client_id,
            order.side,
            order.order_type,
            order.reduce_only,
            expiration=order.expiration,
            match_limit=order.match_limit,
            reflink=self.context.reflink,
        )

    def build_settle_instructions(self) -> CombinableInstructions:
        return CombinableInstructions.empty()

    def build_crank_instructions(
        self, addresses: typing.Sequence[PublicKey], limit: Decimal = Decimal(32)
    ) -> CombinableInstructions:
        if self.perp_market.underlying_perp_market is None:
            raise Exception(
                f"PerpMarket {self.perp_market.symbol} has not been loaded."
            )

        distinct_addresses: typing.List[PublicKey] = [self.account.address]
        for address in addresses:
            if address not in distinct_addresses:
                distinct_addresses += [address]

        if len(distinct_addresses) > limit:
            self._logger.warn(
                f"Cranking limited to {limit} of {len(distinct_addresses)} addresses waiting to be cranked."
            )

        limited_addresses = distinct_addresses[
            0 : min(int(limit), len(distinct_addresses))
        ]
        limited_addresses.sort(key=encode_public_key_for_sorting)
        self._logger.debug(
            f"About to crank {len(limited_addresses)} addresses: {limited_addresses}"
        )

        return build_mango_consume_events_instructions(
            self.context,
            self.group,
            self.perp_market.underlying_perp_market,
            limited_addresses,
            limit,
        )

    def build_redeem_instructions(self) -> CombinableInstructions:
        return build_redeem_accrued_mango_instructions(
            self.context,
            self.wallet,
            self.perp_market,
            self.group,
            self.account,
            self.mngo_token_bank,
        )

    def build_cancel_all_orders_instructions(
        self, limit: Decimal = Decimal(32)
    ) -> CombinableInstructions:
        if self.perp_market.underlying_perp_market is None:
            raise Exception(
                f"PerpMarket {self.perp_market.symbol} has not been loaded."
            )
        return build_cancel_all_perp_orders_instructions(
            self.context,
            self.wallet,
            self.account,
            self.perp_market.underlying_perp_market,
            limit,
        )

    def __str__(self) -> str:
        return """« PerpMarketInstructionBuilder »"""


# # 🥭 PerpMarketOperations
#
# This file deals with placing orders for Perps.
#
class PerpMarketOperations(MarketOperations):
    def __init__(
        self,
        context: Context,
        wallet: Wallet,
        account: Account,
        market_instruction_builder: PerpMarketInstructionBuilder,
    ) -> None:
        super().__init__(market_instruction_builder.perp_market)
        self.context: Context = context
        self.wallet: Wallet = wallet
        self.market_instruction_builder: PerpMarketInstructionBuilder = (
            market_instruction_builder
        )
        self.account: Account = account

    @staticmethod
    def ensure(market_ops: MarketOperations) -> "PerpMarketOperations":
        if not isinstance(market_ops, PerpMarketOperations):
            raise Exception(
                f"MarketOperations for {market_ops.symbol} is not a PerpMarketOperations"
            )
        return market_ops

    @property
    def perp_market(self) -> PerpMarket:
        return self.market_instruction_builder.perp_market

    @property
    def market_name(self) -> str:
        return self.perp_market.symbol

    def cancel_order(
        self, order: Order, ok_if_missing: bool = False
    ) -> typing.Sequence[str]:
        self._logger.info(f"Cancelling {self.market_name} order {order}.")
        signers: CombinableInstructions = CombinableInstructions.from_wallet(
            self.wallet
        )
        cancel: CombinableInstructions = (
            self.market_instruction_builder.build_cancel_order_instructions(
                order, ok_if_missing=ok_if_missing
            )
        )
        crank = self._build_crank(add_self=True)
        settle = self.market_instruction_builder.build_settle_instructions()
        return (signers + cancel + crank + settle).execute(self.context)

    def place_order(
        self, order: Order, crank_limit: Decimal = Decimal(5)
    ) -> typing.Sequence[str]:
        client_id: int = self.context.generate_client_id()
        signers: CombinableInstructions = CombinableInstructions.from_wallet(
            self.wallet
        )
        order_with_client_id: Order = order.with_update(client_id=client_id)
        self._logger.info(f"Placing {self.market_name} order {order_with_client_id}.")
        place: CombinableInstructions = (
            self.market_instruction_builder.build_place_order_instructions(
                order_with_client_id
            )
        )
        crank = self._build_crank(add_self=True, limit=crank_limit)
        settle = self.market_instruction_builder.build_settle_instructions()
        return (signers + place + crank + settle).execute(self.context)

    def settle(self) -> typing.Sequence[str]:
        signers: CombinableInstructions = CombinableInstructions.from_wallet(
            self.wallet
        )
        settle = self.market_instruction_builder.build_settle_instructions()
        return (signers + settle).execute(self.context)

    def crank(self, limit: Decimal = Decimal(32)) -> typing.Sequence[str]:
        signers: CombinableInstructions = CombinableInstructions.from_wallet(
            self.wallet
        )
        crank = self._build_crank(limit=limit)
        return (signers + crank).execute(self.context)

    def create_openorders(self) -> PublicKey:
        return SYSTEM_PROGRAM_ADDRESS

    def ensure_openorders(self) -> PublicKey:
        return SYSTEM_PROGRAM_ADDRESS

    def load_orderbook(self) -> OrderBook:
        return self.perp_market.fetch_orderbook(self.context)

    def load_my_orders(self, include_expired: bool = False) -> typing.Sequence[Order]:
        orderbook: OrderBook = self.load_orderbook()
        return orderbook.all_orders_for_owner(
            self.account.address, include_expired=include_expired
        )

    def _build_crank(
        self, limit: Decimal = Decimal(32), add_self: bool = False
    ) -> CombinableInstructions:
        accounts_to_crank: typing.List[PublicKey] = []
        for event_to_crank in self.perp_market.unprocessed_events(self.context):
            accounts_to_crank += event_to_crank.accounts_to_crank

        if add_self:
            accounts_to_crank += [self.account.address]

        if len(accounts_to_crank) == 0:
            return CombinableInstructions.empty()

        self._logger.debug(
            f"Building crank instruction with {len(accounts_to_crank)} public keys, throttled to {limit}"
        )
        return self.market_instruction_builder.build_crank_instructions(
            accounts_to_crank, limit
        )

    def __str__(self) -> str:
        return f"""« PerpMarketOperations [{self.market_name}] »"""


# # 🥭 PerpMarketStub class
#
# This class holds information to load a `PerpMarket` object but doesn't automatically load it.
#
class PerpMarketStub(Market):
    def __init__(
        self,
        mango_program_address: PublicKey,
        address: PublicKey,
        base: Instrument,
        quote: Token,
        group_address: PublicKey,
    ) -> None:
        super().__init__(
            MarketType.STUB,
            mango_program_address,
            address,
            InventorySource.ACCOUNT,
            base,
            quote,
            RaisingLotSizeConverter(),
        )
        self.group_address: PublicKey = group_address

    def load(
        self, context: Context, group: typing.Optional[Group] = None
    ) -> PerpMarket:
        actual_group: Group = group or Group.load(context, self.group_address)
        underlying_perp_market: PerpMarketDetails = PerpMarketDetails.load(
            context, self.address, actual_group
        )
        return PerpMarket(
            self.program_address,
            self.address,
            self.base,
            self.quote,
            underlying_perp_market,
        )

    @property
    def symbol(self) -> str:
        return f"{self.base.symbol}-PERP"

    def __str__(self) -> str:
        return (
            f"« PerpMarketStub {self.symbol} {self.address} [{self.program_address}] »"
        )
