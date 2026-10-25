"""Сохранение и загрузка трат: JSON — для данных, CSV — для сводки."""
import csv
import json
from pathlib import Path

from models import BudgetTracker, Transaction


class StorageError(Exception):
    """Файл с данными есть, но прочитать его нельзя."""


def save_tracker(tracker: BudgetTracker, path: str | Path) -> None:
    """Сохраняет все траты в JSON. Пишет через временный файл, чтобы не испортить старый."""
    path = Path(path)
    tmp = path.with_suffix(".tmp")
    data = [t.to_dict() for t in tracker.transactions]
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


def load_tracker(path: str | Path) -> BudgetTracker:
    """Читает траты из JSON. Нет файла — пустой трекер. Файл испорчен — StorageError."""
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        return BudgetTracker()
    except json.JSONDecodeError as e:
        raise StorageError(f"Файл {path} повреждён: {e.msg} (строка {e.lineno})") from None
    if not isinstance(data, list):
        raise StorageError(f"В файле {path} ожидался список трат")
    try:
        return BudgetTracker([Transaction.from_dict(item) for item in data])
    except (KeyError, TypeError, ValueError) as e:
        raise StorageError(f"В файле {path} неправильная запись: {e}") from None


def backup_file(path: str | Path) -> Path:
    """Переименовывает испорченный файл в *.broken, чтобы не затереть его при сохранении."""
    path = Path(path)
    backup = path.with_name(path.name + ".broken")
    path.replace(backup)
    return backup


def export_summary_csv(tracker: BudgetTracker, path: str | Path) -> None:
    """Сводка по категориям в CSV: категория, сумма, в конце строка «всего»."""
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["category", "total"])
        for category, amount in tracker.by_category().items():
            writer.writerow([category, f"{amount:.2f}"])
        writer.writerow(["всего", f"{tracker.total():.2f}"])