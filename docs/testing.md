# Testing

Loadwright keeps tests close to the behavior users depend on.

## Local Checks

```bash
go test ./...
go vet ./...
go build -o bin/loadwright ./cmd/loadwright
```

Compile every runnable example:

```bash
mkdir -p /tmp/loadwright-examples
find examples -name '*.yaml' -not -path 'examples/openapi/*' -print | sort | while read -r spec; do
  if grep -q '\${' "$spec"; then
    bin/loadwright compile "$spec" --env-file examples/api/.env.example -o "/tmp/loadwright-examples/$(basename "$spec" .yaml).jmx"
  else
    bin/loadwright compile "$spec" -o "/tmp/loadwright-examples/$(basename "$spec" .yaml).jmx"
  fi
done
```

Import and compile OpenAPI examples:

```bash
mkdir -p /tmp/loadwright-openapi
find examples/openapi -name '*.yaml' -print | sort | while read -r spec; do
  name="$(basename "$spec" .yaml)"
  bin/loadwright import openapi "$spec" -o "/tmp/loadwright-openapi/$name.loadwright.yaml"
  bin/loadwright compile "/tmp/loadwright-openapi/$name.loadwright.yaml" -o "/tmp/loadwright-openapi/$name.jmx"
done
```

## Current Coverage Focus

- Spec validation, defaults, variables, env files, auth, and timeout behavior.
- JMX rendering, including headers, query params, JSON bodies, assertions, duration loads, and timeouts.
- JTL parsing, percentile summaries, threshold pass/fail, and report artifacts.
- CLI parsing and non-Docker command flows.
- OpenAPI import for YAML, JSON, path/query params, request bodies, and error cases.
- Runtime helper behavior for doctor/version parsing.
