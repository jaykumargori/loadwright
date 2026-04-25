# CI

Loadwright is designed to fail CI when performance thresholds are breached.

```bash
go build -o bin/loadwright ./cmd/loadwright
bin/loadwright validate examples/api/basic.yaml
bin/loadwright run examples/api/basic.yaml --ci
```

For environment-specific tests:

```bash
bin/loadwright run loadwright.yaml --env-file .env.ci --ci
```

Use `validate` in fast pull request jobs when you want spec checks without starting JMeter:

```bash
bin/loadwright validate loadwright.yaml --env-file .env.ci
```

The command exits with:

- `0` when JMeter runs successfully and thresholds pass
- `1` when JMeter fails, report parsing fails, or thresholds fail
- `2` for invalid CLI usage

## Example GitHub Actions Step

```yaml
- uses: actions/setup-go@v6
  with:
    go-version: "1.22"
- run: go build -o bin/loadwright ./cmd/loadwright
- run: bin/loadwright run examples/api/basic.yaml --ci
```

For fast pull request checks, compile specs without running load:

```bash
mkdir -p /tmp/loadwright-examples
find examples -name '*.yaml' -not -path 'examples/openapi/*' -print | sort | while read -r spec; do
  if grep -q '\${' "$spec"; then
    bin/loadwright validate "$spec" --env-file examples/api/.env.example
    bin/loadwright compile "$spec" --env-file examples/api/.env.example -o "/tmp/loadwright-examples/$(basename "$spec" .yaml).jmx"
  else
    bin/loadwright validate "$spec"
    bin/loadwright compile "$spec" -o "/tmp/loadwright-examples/$(basename "$spec" .yaml).jmx"
  fi
done
```
