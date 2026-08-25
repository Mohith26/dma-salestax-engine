"""Penny rounding in pure integer arithmetic.

Tax for one jurisdiction layer is base_cents * rate_bps / 10000. The engine
never touches floats: it computes the integer quotient and remainder and then
applies the jurisdiction's documented rounding mode to the remainder.

Modes:
  half_up:   remainder exactly half rounds away from zero (ties up)
  half_down: remainder exactly half rounds toward zero (ties down)
  half_even: remainder exactly half rounds to the even quotient (banker's)

Bases and rates are non negative in this engine, so "away from zero" is up.
"""

MODES = ("half_up", "half_down", "half_even")


def round_div(numerator: int, denominator: int, mode: str) -> int:
    """Round numerator/denominator to the nearest integer under mode."""
    if numerator < 0 or denominator <= 0:
        raise ValueError("round_div expects non negative numerator, positive denominator")
    if mode not in MODES:
        raise ValueError(f"unknown rounding mode: {mode}")
    q, r = divmod(numerator, denominator)
    twice = 2 * r
    if twice > denominator:
        return q + 1
    if twice < denominator:
        return q
    # exact tie
    if mode == "half_up":
        return q + 1
    if mode == "half_down":
        return q
    # half_even
    return q if q % 2 == 0 else q + 1


def line_tax_cents(base_cents: int, rate_bps: int, mode: str) -> int:
    """Tax in whole cents for one jurisdiction layer."""
    return round_div(base_cents * rate_bps, 10000, mode)
