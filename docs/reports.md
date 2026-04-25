# Reports

Each `loadwright run` writes a JMeter result file plus Loadwright summaries.

## Files

- `results.jtl`: raw JMeter CSV output
- `summary.json`: machine-readable summary
- `summary.md`: concise Markdown summary
- `index.html`: standalone human-readable report

## Metrics

Loadwright currently reports:

- total samples
- successful and failed samples
- error rate
- min, max, average
- p50, p90, p95, p99
- per-endpoint count, failures, average, and p95
- threshold pass/fail results

## Thresholds

Thresholds live in the YAML spec:

```yaml
thresholds:
  error_rate_lt: 1
  p95_ms_lt: 3000
  avg_ms_lt: 1000
```

When `--ci` is set, any failed threshold exits with code `1`.
