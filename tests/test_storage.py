"""Тесты сохранения: каждый работает во временной папке tmp_path, настоящие данные не трогаем."""
import json

import pytest

from models import BudgetTracker, Transaction
from storage import StorageError, backup_file, export_summary_csv, load_tracker, save_tracker


def make_tracker() -> BudgetTracker:
    return BudgetTracker([
        Transaction("2026-10-20", "еда", 1250, "продукты"),
        Transaction("2026-10-21", "такси", 320.5, ""),
    ], monthly_limit=5000)


def test_save_and_load_give_same_data(tmp_path):
    path = tmp_path / "expenses.json"
    tracker = make_tracker()
    save_tracker(tracker, path)
    loaded = load_tracker(path)
    assert loaded.transactions == tracker.transactions
    assert loaded.monthly_limit == 5000


def test_missing_file_gives_empty_tracker(tmp_path):
    assert len(load_tracker(tmp_path / "nope.json")) == 0


def test_old_list_format_still_loads(tmp_path):
    path = tmp_path / "expenses.json"
    path.write_text(json.dumps([{"date": "2026-10-20", "category": "еда", "amount": 100}]), encoding="utf-8")
    loaded = load_tracker(path)
    assert len(loaded) == 1
    assert loaded.monthly_limit is None


@pytest.mark.parametrize("content", [
    '[{"date": "2026-10-20",',                                  # обрезанный JSON
    '{"a": 1}',                                                 # не тот формат
    '[{"date": "2026-10-20", "category": "", "amount": 5}]',    # пустая категория
    '[{"date": "2026-10-20", "amount": 5}]',                    # нет поля category
])
def test_broken_file_raises_storage_error(tmp_path, content):
    path = tmp_path / "expenses.json"
    path.write_text(content, encoding="utf-8")
    with pytest.raises(StorageError):
        load_tracker(path)


def test_backup_keeps_broken_file(tmp_path):
    path = tmp_path / "expenses.json"
    path.write_text("мусор", encoding="utf-8")
    backup = backup_file(path)
    assert not path.exists()
    assert backup.read_text(encoding="utf-8") == "мусор"


def test_export_csv(tmp_path):
    path = tmp_path / "summary.csv"
    export_summary_csv(make_tracker(), path)
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    assert lines == ["category,total", "еда,1250.00", "такси,320.50", "всего,1570.50"]