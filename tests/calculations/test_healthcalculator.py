from ..fakes import fake_context
from ..data import load_data_from_directory

from decimal import Decimal
from mango.calculators.healthcalculator import HealthType, HealthCalculator


def test_empty() -> None:
    context = fake_context()
    group, cache, account, open_orders = load_data_from_directory("tests/testdata/empty")

    actual = HealthCalculator(context, HealthType.INITIAL)
    health = actual.calculate(account, open_orders, group, cache)
    # Typescript says: 0
    assert health == Decimal("0")


def test_1deposit() -> None:
    context = fake_context()
    group, cache, account, open_orders = load_data_from_directory("tests/testdata/1deposit")

    actual = HealthCalculator(context, HealthType.INITIAL)
    health = actual.calculate(account, open_orders, group, cache)
    # Typescript says: 37904260000.05905822642118252475
    assert health == Decimal("37904.2600000591928892771752953600134")


def test_account1() -> None:
    context = fake_context()
    group, cache, account, open_orders = load_data_from_directory("tests/testdata/account1")

    actual = HealthCalculator(context, HealthType.INITIAL)
    health = actual.calculate(account, open_orders, group, cache)
    # Typescript says: 454884281.15520619643754685058
    # TODO: This is significantly different from Typescript answer
    assert health == Decimal("2578453.62435039273978679178827388534")


def test_account2() -> None:
    context = fake_context()
    group, cache, account, open_orders = load_data_from_directory("tests/testdata/account2")

    actual = HealthCalculator(context, HealthType.INITIAL)
    health = actual.calculate(account, open_orders, group, cache)
    # Typescript says: 7516159604.84918334545095675026
    # TODO: This is slightly different from Typescript answer
    assert health == Decimal("-34471.8822627460347363357247598728190")


def test_account3() -> None:
    context = fake_context()
    group, cache, account, open_orders = load_data_from_directory("tests/testdata/account3")

    actual = HealthCalculator(context, HealthType.INITIAL)
    health = actual.calculate(account, open_orders, group, cache)

    # Typescript says: 341025333625.51856223547208912805
    # TODO: This is significantly different from Typescript answer
    assert health == Decimal("7036880.69722812395986194177339495613")


def test_account4() -> None:
    context = fake_context()
    group, cache, account, open_orders = load_data_from_directory("tests/testdata/account4")

    actual = HealthCalculator(context, HealthType.INITIAL)
    health = actual.calculate(account, open_orders, group, cache)
    # Typescript says: -848086876487.04950427436299875694
    # TODO: This is significantly different from Typescript answer
    assert health == Decimal("1100318.49506000114695611699892507857")
