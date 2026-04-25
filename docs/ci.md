# CI

Loadwright is designed to fail CI when performance thresholds are breached.

```bash
go build -o bin/loadwright ./cmd/loadwright
bin/loadwright run examples/api/basic.yaml --ci
```

The command exits with:

- `0` when JMeter runs successfully and thresholds pass
- `1` when JMeter fails, report parsing fails, or thresholds fail
- `2` for invalid CLI usage

## Example GitHub Actions Step

```yaml
- uses: actions/setup-go@v5
  with:
    go-version: "1.22"
- run: go build -o bin/loadwright ./cmd/loadwright
- run: bin/loadwright run examples/api/basic.yaml --ci
```

For fast pull request checks, compile specs without running load:

```bash
for spec in examples/**/*.yaml; do
  bin/loadwright compile "$spec" -o "/tmp/loadwright-examples/$(basename "$spec" .yaml).jmx"
done
```
