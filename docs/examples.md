# Examples

The `examples/` directory contains runnable specs for common scenarios.

## Basic API

```bash
bin/loadwright run examples/api/basic.yaml --ci
```

Demonstrates a GET request, a POST JSON request, status assertions, and passing thresholds.

## Query Params

```bash
bin/loadwright run examples/api/query-params.yaml --ci
```

Demonstrates query-string parameters on a GET request.

## POST JSON

```bash
bin/loadwright run examples/api/post-json.yaml --ci
```

Demonstrates JSON request bodies and custom headers.

## Duration Load

```bash
bin/loadwright run examples/api/duration-load.yaml --ci
```

Demonstrates duration-based load instead of a fixed loop count.

## Threshold Failure

```bash
bin/loadwright run examples/api/threshold-fail.yaml --ci
```

Demonstrates CI failure behavior. This example intentionally uses an unrealistic p95 threshold.
