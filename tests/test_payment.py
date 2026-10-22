import pytest

from app import calculate_booking_price


def test_calculate_booking_price_for_tour():
    assert calculate_booking_price('dhow', 2) == 17000
    assert calculate_booking_price('sandbank', 1) == 7000


def test_calculate_booking_price_for_hotel():
    assert calculate_booking_price('shela-guest-house', 2) == 9000
    assert calculate_booking_price('manda-ocean-villa', 2) == 32000


def test_calculate_booking_price_unknown_tour():
    with pytest.raises(ValueError):
        calculate_booking_price('unknown-tour', 2)
