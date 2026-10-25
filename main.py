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
3. История с сортировкой
4. Сводка по категориям
5. Самая крупная трата
6. Фильтр по категории
7. Изменить расход
8. Удалить расход
9. Месячный лимит
10. Экспорт сводки в CSV
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


def parse_sort_field(text: str) -> str:
    fields = {"1": "date", "2": "amount"}
    if text not in fields:
        raise ValueError("Введи 1 (по дате) или 2 (по сумме)")
    return fields[text]


def parse_limit(text: str) -> float | None:
    return None if text == "" else Transaction.parse_amount(text)


def keep_or(parse, old):
    """Для редактирования: пустой ввод — оставить старое значение, иначе проверить новое."""
    return lambda text: old if text == "" else parse(text)


def ask_transaction() -> Transaction:
    date = ask_valid("Дата (ГГГГ-ММ-ДД, Enter — сегодня): ", parse_date_or_today)
    category = ask_valid("Категория: ", Transaction.parse_category)
    amount = ask_valid("Сумма: ", Transaction.parse_amount)
    comment = input("Комментарий (можно пусто): ").strip()
    return Transaction(date, category, amount, comment)


# ---------- действия меню ----------
def report_month(tracker: BudgetTracker, day: dt.date) -> None:
    """Сколько потрачено за месяц этой даты и не превышен ли лимит."""
    limit = tracker.monthly_limit
    if limit is None:
        return
    spent = tracker.month_total(day.year, day.month)
    if spent > limit:
        print(f"ВНИМАНИЕ: лимит на {day:%m.%Y} превышен на {spent - limit:.2f} ₽ ({spent:.2f} из {limit:.2f})")
    else:
        print(f"За {day:%m.%Y} потрачено {spent:.2f} из {limit:.2f} ₽, осталось {limit - spent:.2f}")


def add_expense(tracker: BudgetTracker) -> None:
    t = ask_transaction()
    tracker.add(t)
    print(f"Добавлено: {t}")
    report_month(tracker, t.date)


def show_history(tracker: BudgetTracker) -> None:
    if not tracker:
        print("Пока пусто.")
        return
    for number, t in enumerate(tracker.transactions, start=1):
        print(f"{number:>3}. {t}")
    print(f"     {tracker}")


def show_sorted(tracker: BudgetTracker) -> None:
    if not tracker:
        print("Пока пусто.")
        return
    field = ask_valid("Сортировать: 1 — по дате, 2 — по сумме: ", parse_sort_field)
    reverse = input("По убыванию? (д — да, Enter — нет): ").strip().lower() in ("д", "да", "y")
    for number, t in tracker.sorted_by(field, reverse):
        print(f"{number:>3}. {t}")              # номер — как в истории, для удаления и правки


def show_summary(tracker: BudgetTracker) -> None:
    if not tracker:
        print("Пока пусто.")
        return
    total = tracker.total()
    for category, amount in tracker.by_category().items():
        print(f"  {category:<12} {amount:>10.2f} ₽  {amount / total:6.1%}")
    print(f"  {'всего':<12} {total:>10.2f} ₽")
    report_month(tracker, dt.date.today())


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


def edit_expense(tracker: BudgetTracker) -> None:
    show_history(tracker)
    if not tracker:
        return
    number = ask_valid("Номер траты для изменения: ", parse_number)
    old = tracker.get(number - 1)
    print("Enter — оставить как было.")
    date = ask_valid(f"Дата [{old.date}]: ", keep_or(Transaction.parse_date, old.date))
    category = ask_valid(f"Категория [{old.category}]: ", keep_or(Transaction.parse_category, old.category))
    amount = ask_valid(f"Сумма [{old.amount:.2f}]: ", keep_or(Transaction.parse_amount, old.amount))
    comment = input(f"Комментарий [{old.comment}]: ").strip() or old.comment
    new = Transaction(date, category, amount, comment)
    tracker.replace(number - 1, new)
    print(f"Было:  {old}\nСтало: {new}")
    report_month(tracker, new.date)


def delete_expense(tracker: BudgetTracker) -> None:
    show_history(tracker)
    if not tracker:
        return
    number = ask_valid("Номер траты для удаления: ", parse_number)
    removed = tracker.remove(number - 1)          # нет такого номера → ValueError, его поймает main
    print(f"Удалено: {removed}")


def set_limit(tracker: BudgetTracker) -> None:
    current = f"{tracker.monthly_limit:.2f} ₽" if tracker.monthly_limit else "нет"
    print(f"Сейчас лимит: {current}")
    limit = ask_valid("Новый лимит на месяц (Enter — без лимита): ", parse_limit)
    tracker.set_limit(limit)
    print(f"Лимит: {limit:.2f} ₽" if limit else "Лимит снят.")
    report_month(tracker, dt.date.today())


def export_csv(tracker: BudgetTracker) -> None:
    path = DATA_FILE.with_name("summary.csv")
    export_summary_csv(tracker, path)
    print(f"Сводка сохранена в {path.name}")


ACTIONS = {
    "1": add_expense,
    "2": show_history,
    "3": show_sorted,
    "4": show_summary,
    "5": show_biggest,
    "6": filter_category,
    "7": edit_expense,
    "8": delete_expense,
    "9": set_limit,
    "10": export_csv,
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