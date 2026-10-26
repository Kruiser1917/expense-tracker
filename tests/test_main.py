"""Тесты ввода: подменяем input(), чтобы проверить меню без человека."""
import pytest

from main import ask_valid, keep_or, parse_number
from models import Transaction


def test_parse_number():
    assert parse_number("2") == 2
    for bad in ("", "abc", "-1", "1.5"):
        with pytest.raises(ValueError):
            parse_number(bad)


def test_keep_or_keeps_old_value_on_enter():
    parse = keep_or(Transaction.parse_amount, 320.0)
    assert parse("") == 320.0
    assert parse("800") == 800.0
    with pytest.raises(ValueError):
        parse("сто")


def test_ask_valid_asks_again_until_answer_is_valid(monkeypatch, capsys):
    answers = iter(["сто", "-5", "450"])
    monkeypatch.setattr("builtins.input", lambda prompt: next(answers))
    assert ask_valid("Сумма: ", Transaction.parse_amount) == 450.0
    assert capsys.readouterr().out.count("Ошибка") == 2