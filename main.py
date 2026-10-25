"""Консольный трекер расходов: меню, ввод и вывод."""
import datetime as dt
from pathlib import Path

from models import BudgetTracker, Transaction
from storage import StorageError, backup_file, export_summary_csv, load_tracker, save_tracker

DATA_FILE = Path(__file__).with_name("expenses.json")   # рядом с main.py, откуда бы ни запускали

MENU = """
=== Трекер расходов ===
1. Добавить расход
2. История
3. Сводка по категориям
4. Самая крупная трата
5. Фильтр по категории
6. Удалить расход
7. Экспорт сводки в CSV
0. Выход"""


# ---------- ввод ----------
def ask_valid(prompt: str, parse):
    """Спрашивает, пока parse не примет ответ. Ошибку показывает и спрашивает снова."""
    while True:
        try:
            return parse(input(prompt).strip())
        except ValueError as e:
            print(f"  Ошибка: {e}")


def parse_date_or_today(text: str) -> dt.date:
    return dt.date.today() if text == "" else Transaction.parse_date(text)


def parse_number(text: str) -> int:
    if not text.isdigit():
        raise ValueError("Нужен номер из списка, например 2")
    return int(text)


def ask_transaction() -> Transaction:
    date = ask_valid("Дата (ГГГГ-ММ-ДД, Enter — сегодня): ", parse_date_or_today)
    category = ask_valid("Категория: ", Transaction.parse_category)
    amount = ask_valid("Сумма: ", Transaction.parse_amount)
    comment = input("Комментарий (можно пусто): ").strip()
    return Transaction(date, category, amount, comment)


# ---------- действия меню ----------
def add_expense(tracker: BudgetTracker) -> None:
    t = ask_transaction()
    tracker.add(t)
    print(f"Добавлено: {t}")


def show_history(tracker: BudgetTracker) -> None:
    if not tracker:
        print("Пока пусто.")
        return
    for number, t in enumerate(tracker.transactions, start=1):
        print(f"{number:>3}. {t}")
    print(f"     {tracker}")


def show_summary(tracker: BudgetTracker) -> None:
    if not tracker:
        print("Пока пусто.")
        return
    total = tracker.total()
    for category, amount in tracker.by_category().items():
        print(f"  {category:<12} {amount:>10.2f} ₽  {amount / total:6.1%}")
    print(f"  {'всего':<12} {total:>10.2f} ₽")


def show_biggest(tracker: BudgetTracker) -> None:
    t = tracker.biggest()
    print(t if t else "Пока пусто.")


def filter_category(tracker: BudgetTracker) -> None:
    category = input("Категория: ").strip()
    found = tracker.filter_by_category(category)
    if not found:
        known = ", ".join(tracker.by_category()) or "—"
        print(f"В категории «{category}» трат нет. Есть категории: {known}")
        return
    for t in found:
        print(f"  {t}")
    print(f"  Итого: {sum(t.amount for t in found):.2f} ₽")


def delete_expense(tracker: BudgetTracker) -> None:
    show_history(tracker)
    if not tracker:
        return
    number = ask_valid("Номер траты для удаления: ", parse_number)
    removed = tracker.remove(number - 1)          # нет такого номера → ValueError, его поймает main
    print(f"Удалено: {removed}")


def export_csv(tracker: BudgetTracker) -> None:
    path = DATA_FILE.with_name("summary.csv")
    export_summary_csv(tracker, path)
    print(f"Сводка сохранена в {path.name}")


ACTIONS = {
    "1": add_expense,
    "2": show_history,
    "3": show_summary,
    "4": show_biggest,
    "5": filter_category,
    "6": delete_expense,
    "7": export_csv,
}


# ---------- запуск ----------
def open_tracker(path: Path) -> BudgetTracker:
    try:
        return load_tracker(path)
    except StorageError as e:
        print(f"Внимание: {e}")
        print(f"Испорченный файл сохранён как {backup_file(path).name}, начинаю с пустого списка.")
        return BudgetTracker()


def main() -> None:
    tracker = open_tracker(DATA_FILE)
    while True:
        print(MENU)
        choice = input("> ").strip()
        if choice == "0":
            break
        action = ACTIONS.get(choice)
        if action is None:
            print("Нет такого пункта — введи цифру из меню.")
            continue
        try:
            action(tracker)
        except ValueError as e:
            print(f"Ошибка: {e}")
        save_tracker(tracker, DATA_FILE)          # сохраняем после каждого действия
    print(f"Пока! Данные в {DATA_FILE.name}")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nВыход. Всё, что успели добавить, уже сохранено.")