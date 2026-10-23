"""Estimated standard API costs, not provider billing or account balance.

Rates checked 2026-10-23 against developers.openai.com/api/docs/models/
gpt-4.1-mini and gpt-4.1. USD per million tokens; no Batch API used here.
"""
from decimal import Decimal

RATES = {
    'gpt-4.1-mini': ('0.40', '0.10', '1.60'),
    'gpt-4.1-mini-2025-04-14': ('0.40', '0.10', '1.60'),
    'gpt-4.1': ('2.00', '0.50', '8.00'),
    'gpt-4.1-2025-04-14': ('2.00', '0.50', '8.00'),
}


def summarize(rows):
    total = month = Decimal(0)
    included = excluded = 0
    models = {}
    for row in rows:
        rates = RATES.get(row['model'])
        if not rates or not row['has_usage']:
            excluded += row['count']
            continue
        inp, cached, out = map(Decimal, rates)
        cost = ((row['input_tokens'] - row['cached_tokens']) * inp
                + row['cached_tokens'] * cached + row['output_tokens'] * out) / 1000000
        included += row['count']
        total += cost
        if row['this_month']:
            month += cost
        models[row['model']] = models.get(row['model'], Decimal(0)) + cost
    return {'estimated_total_usd': float(total), 'estimated_month_usd': float(month),
            'estimated_average_usd': float(total / included) if included else None,
            'included_reports': included, 'excluded_reports': excluded,
            'models': [{'model': key, 'estimated_usd': float(value)} for key, value in sorted(models.items())],
            'rates_checked': '2026-10-23', 'currency': 'USD', 'basis': 'saved_reports_only'}


def saved_report_costs(db):
    rows = db.execute("""WITH usage AS (
        SELECT data->>'model' AS model,
            (created AT TIME ZONE 'UTC') >= date_trunc('month', now() AT TIME ZONE 'UTC') AS this_month,
            coalesce(jsonb_typeof(data->'usage'->'prompt_tokens')='number'
                AND jsonb_typeof(data->'usage'->'completion_tokens')='number', false) AS has_usage,
            greatest(coalesce((data->'usage'->>'prompt_tokens')::bigint,0),0) AS input_tokens,
            greatest(coalesce((data->'usage'->'prompt_tokens_details'->>'cached_tokens')::bigint,0),0) AS cached_tokens,
            greatest(coalesce((data->'usage'->>'completion_tokens')::bigint,0),0) AS output_tokens
        FROM reports)
        SELECT model, this_month, has_usage, count(*) AS count,
            sum(input_tokens) AS input_tokens, sum(least(cached_tokens,input_tokens)) AS cached_tokens,
            sum(output_tokens) AS output_tokens FROM usage GROUP BY model,this_month,has_usage""").fetchall()
    return summarize(rows)
