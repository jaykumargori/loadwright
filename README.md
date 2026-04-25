# Loadwright

Docker-first, spec-driven JMeter automation.

loadwright turns readable YAML specs into portable JMeter `.jmx` test plans, runs them through Dockerized JMeter, and emits reports that work well locally and in CI.

This repository still contains the original Python prototype as reference code. The public OSS direction is the Go CLI under `cmd/` and `internal/`.

## Why This Exists

JMeter is powerful, but the day-to-day workflow can be awkward: JMX XML, local Java/JMeter setup, Docker wiring, plugin handling, reports, and CI thresholds. Loadwright keeps JMeter compatibility while giving teams a small CLI and reviewable specs.

Use Loadwright when you want:

- a readable YAML source of truth for load tests
- Dockerized JMeter runs without local JMeter setup
- JSON, Markdown, and HTML summaries
- CI pass/fail thresholds
- future optional AI assistance without depending on AI for normal runs

## Install From Source

Requires Go 1.22+ and Docker.

```bash
go build -o bin/loadwright ./cmd/loadwright
```

## Quickstart

Create a starter spec:

```bash
bin/loadwright init
```

Or use the included example:

```bash
bin/loadwright compile examples/api/basic.yaml -o tests/httpbin-basic.jmx
bin/loadwright run examples/api/basic.yaml --ci
```

Check local prerequisites:

```bash
bin/loadwright doctor
bin/loadwright doctor --deep
```

Reports are written to `results/<run-id>/`:

- `results.jtl`
- `summary.json`
- `summary.md`
- `index.html`

## Example Spec

```yaml
name: httpbin-basic
target: https://httpbin.org
load:
  users: 5
  ramp_up: 10s
  loops: 3
requests:
  - name: get status
    method: GET
    path: /status/200
    expect:
      status: 200
thresholds:
  error_rate_lt: 1
  p95_ms_lt: 3000
```

See [docs/spec-reference.md](docs/spec-reference.md) for the current spec format.

More docs:

- [Getting started](docs/getting-started.md)
- [Examples](docs/examples.md)
- [OpenAPI import](docs/openapi-import.md)
- [Data sources](docs/data-sources.md)
- [CI](docs/ci.md)
- [Reports](docs/reports.md)
- [Testing](docs/testing.md)

## Commands

```bash
loadwright doctor [--deep] [--image justb4/jmeter:latest]
loadwright init [path]
loadwright compile <spec.yaml> [-o tests/name.jmx] [--env-file .env.test]
loadwright run <spec.yaml|test.jmx> [--out-dir results/run] [--env-file .env.test] [--ci]
```

`doctor --deep` runs the configured JMeter Docker image and verifies that JMeter starts.

## Roadmap

See [ROADMAP.md](ROADMAP.md). The short version:

- make the deterministic Go CLI excellent first
- add OpenAPI/Postman/HAR import next
- add WebSocket/plugin automation
- add optional AI later for generating, explaining, and improving specs

## Development

```bash
go test ./...
```

## License

Apache-2.0.
