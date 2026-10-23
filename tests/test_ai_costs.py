import pytest
from ai_costs import summarize


def row(model='gpt-4.1-mini-2025-04-14', **changes):
    return dict(dict(model=model, this_month=True, has_usage=True, count=1,
                     input_tokens=1000000, cached_tokens=200000, output_tokens=100000), **changes)


def test_mixed_models_cached_tokens_and_month():
    result = summarize([row(), row('gpt-4.1-2025-04-14', this_month=False)])
    # Mini: .32 + .02 + .16 = .50; full: 1.60 + .10 + .80 = 2.50.
    assert result['estimated_total_usd'] == pytest.approx(3)
    assert result['estimated_month_usd'] == pytest.approx(.5)
    assert result['estimated_average_usd'] == pytest.approx(1.5)


def test_unknown_and_missing_usage_are_excluded_not_free():
    result = summarize([row('unknown'), row(has_usage=False)])
    assert result['excluded_reports'] == 2 and result['included_reports'] == 0
    assert result['estimated_average_usd'] is None
    assert summarize([])['models'] == []
