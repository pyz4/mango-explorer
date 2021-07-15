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


from decimal import Decimal

from .account import Account
from .combinableinstructions import CombinableInstructions
from .context import Context
from .group import Group
from .marketinstructionbuilder import MarketInstructionBuilder
from .instructions import build_cancel_perp_order_instructions, build_mango_consume_events_instructions, build_place_perp_order_instructions
from .orders import Order
from .perpmarket import PerpMarket
from .wallet import Wallet


# # 🥭 PerpMarketInstructionBuilder
#
# This file deals with building instructions for Perp markets.
#
# As a matter of policy for all InstructionBuidlers, construction and build_* methods should all work with
# existing data, requiring no fetches from Solana or other sources. All necessary data should all be loaded
# on initial setup in the `load()` method.
#

class PerpMarketInstructionBuilder(MarketInstructionBuilder):
    def __init__(self, context: Context, wallet: Wallet, group: Group, account: Account, perp_market: PerpMarket):
        super().__init__()
        self.context: Context = context
        self.wallet: Wallet = wallet
        self.group: Group = group
        self.account: Account = account
        self.perp_market: PerpMarket = perp_market

    @staticmethod
    def load(context: Context, wallet: Wallet, group: Group, account: Account, perp_market: PerpMarket) -> "PerpMarketInstructionBuilder":
        return PerpMarketInstructionBuilder(context, wallet, group, account, perp_market)

    def build_cancel_order_instructions(self, order: Order) -> CombinableInstructions:
        return build_cancel_perp_order_instructions(
            self.context, self.wallet, self.account, self.perp_market, order)

    def build_place_order_instructions(self, order: Order) -> CombinableInstructions:
        return build_place_perp_order_instructions(
            self.context, self.wallet, self.perp_market.group, self.account, self.perp_market, order.price, order.quantity, order.client_id, order.side, order.order_type)

    def build_settle_instructions(self) -> CombinableInstructions:
        return CombinableInstructions.empty()

    def build_crank_instructions(self, limit: Decimal = Decimal(32)) -> CombinableInstructions:
        return build_mango_consume_events_instructions(self.context, self.wallet, self.group, self.account, self.perp_market, limit)

    def __str__(self) -> str:
        return """« 𝙿𝚎𝚛𝚙𝙼𝚊𝚛𝚔𝚎𝚝𝙸𝚗𝚜𝚝𝚛𝚞𝚌𝚝𝚒𝚘𝚗𝚜 »"""
