"""Unit tests for expand_address."""
import pytest
from address_finder import expand_address


def test_french_expansion():
    result = expand_address("Quatre vingt douze R. de la Roquette")
    assert any("92" in r for r in result)


def test_abbreviation_expansion():
    result = expand_address("123 Main St")
    assert any("street" in r for r in result)


def test_returns_list():
    result = expand_address("1 Av. des Champs-Elysées Paris")
    assert isinstance(result, list)
    assert len(result) >= 1
