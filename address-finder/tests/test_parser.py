"""Unit tests for parse_address (requires installed libpostal + data)."""
import pytest
from address_finder import parse_address


def test_us_address():
    result = dict(parse_address("781 Franklin Ave Brooklyn NYC NY 11216 USA"))
    assert result.get("house_number") == "781"
    assert "franklin ave" in result.get("road", "")
    assert result.get("country") == "usa"


def test_german_address():
    result = dict(parse_address("Platz der Republik 1, 11011 Berlin"))
    assert result.get("house_number") == "1"
    assert result.get("city") == "berlin"


def test_empty_input():
    assert parse_address("") == []


def test_returns_list_of_tuples():
    result = parse_address("10 Downing Street London")
    assert isinstance(result, list)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in result)
