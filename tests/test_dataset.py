import pytest

from taxgrid.dataset import parse_date


def test_jurisdiction_count_meets_floor(ds):
    assert len(ds.jurisdictions) >= 200


def test_all_levels_present(ds):
    levels = {j.level for j in ds.jurisdictions.values()}
    assert levels == {"state", "county", "city", "special"}


def test_every_city_stack_starts_state_county_city(ds):
    for city_id, stack in ds.stack_by_city.items():
        assert stack[0].startswith("ST-")
        assert stack[1].startswith("CO-")
        assert stack[2] == city_id
        for extra in stack[3:]:
            assert extra.startswith("SP-")


def test_category_floor(ds):
    assert len(ds.categories) >= 20


def test_matrix_covers_every_state_and_category(ds):
    states = [j.state for j in ds.jurisdictions.values() if j.level == "state"]
    for s in states:
        for c in ds.categories:
            rule = ds.taxability(s, c)
            assert rule["kind"] in ("taxable", "exempt", "threshold")


def test_rate_tables_sorted_and_nonnegative(ds):
    for j in ds.jurisdictions.values():
        assert j.table.ordinals == sorted(j.table.ordinals)
        assert all(r >= 0 for r in j.table.rates)


def test_unknown_city_rejected(ds):
    with pytest.raises(KeyError):
        ds.city("CI-XX-99-9")
    with pytest.raises(KeyError):
        ds.city("ST-CD")


def test_unknown_category_rejected(ds):
    with pytest.raises(KeyError):
        ds.taxability("CD", "spaceships")


def test_rate_before_first_effective_date_is_none(ds):
    j = ds.jurisdictions["ST-CD"]
    assert j.table.rate_on(parse_date("2019-12-31")) is None
    assert j.table.rate_on(parse_date("2020-01-01")) == 573
