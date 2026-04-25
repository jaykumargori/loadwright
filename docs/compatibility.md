# Compatibility

Loadwright is a Go CLI that generates JMeter-compatible `.jmx` files and runs them through Docker.

## Go

Development and CI target Go 1.22 or newer.

## Operating Systems

Release builds target:

- macOS arm64 and amd64
- Linux arm64 and amd64
- Windows amd64

## JMeter

Generated plans target Apache JMeter 5.6.x-era JMX properties. The default runtime image is:

```text
justb4/jmeter:latest
```

Use `loadwright doctor --deep` to verify that the configured image starts on your machine.

## Docker

Docker is required for `loadwright run` and `loadwright doctor --deep`.

Docker is not required for:

- `loadwright init`
- `loadwright validate`
- `loadwright compile`
- `loadwright import openapi`
- `loadwright report`

## Spec Stability

Before `v1.0.0`, the YAML spec can still evolve. Changes should be documented in `CHANGELOG.md`, and breaking changes should include migration notes.

After `v1.0.0`, compatible additions should be preferred over breaking field changes.
