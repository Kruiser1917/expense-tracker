"""Тесты моделей: обычные, граничные и ошибочные данные."""
import datetime as dt

import pytest

from models import BudgetTracker, Transaction


@pytest.fixture
def tracker() -> BudgetTracker:
    """Трекер с четырьмя тратами — свежий для каждого теста."""
    return BudgetTracker([
        Transaction("2026-10-20", "еда", 1250, "продукты"),
        Transaction("2026-10-21", "такси", 320, "до офиса"),
        Transaction("2026-10-22", "еда", 450, "обед"),
        Transaction("2026-09-30", "кино", 900, "дюна"),
    ])


# ---------- Transaction ----------
def test_transaction_cleans_input():
    t = Transaction(" 2026-10-24 ", "  Еда ", "450,5", " обед ")
    assert t.date == dt.date(2026, 10, 24)
    assert t.category == "еда"
    assert t.amount == 450.5
    assert t.comment == "обед"


def test_to_dict_and_back_gives_same_transaction():
    t = Transaction("2026-10-24", "еда", 450, "обед")
    assert Transaction.from_dict(t.to_dict()) == t


def test_smallest_amount_is_ok():
    assert Transaction("2026-10-24", "еда", "0.01").amount == 0.01      # граница: 1 копейка


@pytest.mark.parametrize("date, category, amount", [
    ("2026-13-01", "еда", 100),     # нет 13-го месяца
    ("вчера", "еда", 100),
    ("2026-10-24", "   ", 100),     # пустая категория
    ("2026-10-24", "еда", 0),       # граница: ноль
    ("2026-10-24", "еда", -5),
    ("2026-10-24", "еда", "сто"),
    ("2026-10-24", "еда", "nan"),
])
def test_bad_transaction_raises(date, category, amount):
    with pytest.raises(ValueError):
        Transaction(date, category, amount)


# ---------- BudgetTracker ----------
def test_total_and_by_category(tracker):
    assert tracker.total() == 2920
    assert tracker.by_category() == {"еда": 1700, "кино": 900, "такси": 320}
    assert list(tracker.by_category()) == ["еда", "кино", "такси"]      # от большего к меньшему


def test_empty_tracker():
    empty = BudgetTracker()
    assert len(empty) == 0
    assert empty.total() == 0
    assert empty.by_category() == {}
    assert empty.biggest() is None


def test_biggest_and_filter(tracker):
    assert tracker.biggest().comment == "продукты"
    assert [t.amount for t in tracker.filter_by_category(" ЕДА ")] == [1250, 450]
    assert tracker.filter_by_category("такого нет") == []


def test_remove_and_bad_index(tracker):
    removed = tracker.remove(1)
    assert removed.category == "такси"
    assert len(tracker) == 3
    for bad in (-1, 3, 100):
        with pytest.raises(ValueError):
            tracker.remove(bad)


def test_replace(tracker):
    new = Transaction("2026-10-21", "такси", 800, "аэропорт")
    old = tracker.replace(1, new)
    assert old.amount == 320
    assert tracker.get(1) == new


def test_sorted_keeps_history_numbers(tracker):
    by_amount = tracker.sorted_by("amount", reverse=True)
    assert [number for number, _ in by_amount] == [1, 4, 3, 2]
    assert [t.amount for _, t in by_amount] == [1250, 900, 450, 320]
    with pytest.raises(ValueError):
        tracker.sorted_by("comment")


def test_month_total_and_limit(tracker):
    assert tracker.month_total(2026, 10) == 2020
    assert tracker.month_total(2026, 9) == 900
    tracker.set_limit(5000)
    assert tracker.monthly_limit == 5000
    tracker.set_limit(None)
    assert tracker.monthly_limit is None
    with pytest.raises(ValueError):
        tracker.set_limit(0)