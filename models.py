"""Модели трекера расходов: транзакция и трекер."""
import datetime as dt
import math


class Transaction:
    """Одна трата: дата, категория, сумма и комментарий."""

    def __init__(self, date: dt.date | str, category: str, amount: float | str, comment: str = "") -> None:
        self.date = self.parse_date(date)
        self.category = self.parse_category(category)
        self.amount = self.parse_amount(amount)
        self.comment = str(comment).strip()

    # --- проверки: плохие данные → ValueError с понятным текстом ---
    @staticmethod
    def parse_date(value: dt.date | str) -> dt.date:
        if isinstance(value, dt.date):
            return value
        try:
            return dt.date.fromisoformat(str(value).strip())
        except ValueError:
            raise ValueError("Дата должна быть в формате ГГГГ-ММ-ДД, например 2026-10-24") from None

    @staticmethod
    def parse_category(value: str) -> str:
        category = str(value).strip().lower()
        if not category:
            raise ValueError("Категория не может быть пустой")
        return category

    @staticmethod
    def parse_amount(value: float | str) -> float:
        try:
            amount = float(str(value).replace(",", "."))
        except ValueError:
            raise ValueError("Сумма должна быть числом, например 450 или 99.90") from None
        if not math.isfinite(amount) or amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
        return round(amount, 2)

    # --- как объект выглядит и сравнивается ---
    def __str__(self) -> str:
        return f"{self.date.isoformat()} | {self.category:<12} | {self.amount:>10.2f} ₽ | {self.comment}"

    def __repr__(self) -> str:
        return f"Transaction({self.date.isoformat()!r}, {self.category!r}, {self.amount}, {self.comment!r})"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Transaction) and self.to_dict() == other.to_dict()

    # --- перевод в словарь и обратно (понадобится для JSON) ---
    def to_dict(self) -> dict:
        return {"date": self.date.isoformat(), "category": self.category,
                "amount": self.amount, "comment": self.comment}

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction":
        return cls(data["date"], data["category"], data["amount"], data.get("comment", ""))

class BudgetTracker:
    """Список трат и операции над ним: добавить, удалить, посчитать, найти."""

    def __init__(self, transactions: list[Transaction] | None = None) -> None:
        self.transactions: list[Transaction] = list(transactions) if transactions else []

    def __len__(self) -> int:
        return len(self.transactions)

    def __str__(self) -> str:
        return f"BudgetTracker: записей {len(self)}, всего {self.total():.2f} ₽"

    def add(self, transaction: Transaction) -> None:
        self.transactions.append(transaction)

    def remove(self, index: int) -> Transaction:
        """Удаляет трату по индексу (с нуля) и возвращает её."""
        if not 0 <= index < len(self.transactions):
            raise ValueError(f"Нет траты с номером {index + 1}")
        return self.transactions.pop(index)

    def total(self) -> float:
        return round(sum(t.amount for t in self.transactions), 2)

    def by_category(self) -> dict[str, float]:
        """Сумма по каждой категории, от самой затратной к самой дешёвой."""
        totals: dict[str, float] = {}
        for t in self.transactions:
            totals[t.category] = totals.get(t.category, 0) + t.amount
        ordered = sorted(totals.items(), key=lambda pair: pair[1], reverse=True)
        return {category: round(amount, 2) for category, amount in ordered}

    def biggest(self) -> Transaction | None:
        """Самая крупная трата или None, если трат нет."""
        return max(self.transactions, key=lambda t: t.amount, default=None)

    def filter_by_category(self, category: str) -> list[Transaction]:
        wanted = category.strip().lower()
        return [t for t in self.transactions if t.category == wanted]