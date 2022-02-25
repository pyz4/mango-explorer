from .context import mango
from .fakes import fake_account_info, fake_public_key

from decimal import Decimal


def test_constructor() -> None:
    account_info = fake_account_info()
    program_address = fake_public_key()
    market = fake_public_key()
    owner = fake_public_key()

    flags = mango.AccountFlags(
        mango.Version.V1, True, False, True, False, False, False, False, False
    )
    actual = mango.OpenOrders(
        account_info,
        mango.Version.V1,
        program_address,
        flags,
        market,
        owner,
        Decimal(0),
        Decimal(0),
        Decimal(0),
        Decimal(0),
        [],
        Decimal(0),
    )
    assert actual is not None
