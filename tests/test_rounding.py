import pytest

from taxgrid.rounding import line_tax_cents, round_div


def test_exact_division_no_rounding():
    assert round_div(573 * 10000, 10000, "half_up") == 573


def test_below_half_rounds_down_all_modes():
    for mode in ("half_up", "half_down", "half_even"):
        assert round_div(12499, 1000, mode) == 12


def test_above_half_rounds_up_all_modes():
    for mode in ("half_up", "half_down", "half_even"):
        assert round_div(12501, 1000, mode) == 13


def test_half_up_tie():
    assert round_div(125, 10, "half_up") == 13


def test_half_down_tie():
    assert round_div(125, 10, "half_down") == 12


def test_half_even_tie_rounds_to_even():
    assert round_div(125, 10, "half_even") == 12
    assert round_div(135, 10, "half_even") == 14


def test_zero_numerator():
    for mode in ("half_up", "half_down", "half_even"):
        assert round_div(0, 10000, mode) == 0


def test_negative_numerator_rejected():
    with pytest.raises(ValueError):
        round_div(-1, 10000, "half_up")


def test_bad_mode_rejected():
    with pytest.raises(ValueError):
        round_div(1, 10000, "nearest")


def test_bad_denominator_rejected():
    with pytest.raises(ValueError):
        round_div(1, 0, "half_up")


def test_line_tax_cents_tie_examples():
    # 12.5 cents exact tie: 2500 cents at 50 bps
    assert line_tax_cents(2500, 50, "half_up") == 13
    assert line_tax_cents(2500, 50, "half_down") == 12
    assert line_tax_cents(2500, 50, "half_even") == 12


def test_line_tax_cents_matches_manual():
    # 11000 * 693 bps = 762.3 cents
    assert line_tax_cents(11000, 693, "half_up") == 762
