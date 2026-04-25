package cli

import (
	"bytes"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestParseCompileArgsAcceptsFlagsAfterSpec(t *testing.T) {
	specPath, output, envFile, err := parseCompileArgs([]string{"spec.yaml", "-o", "tests/spec.jmx", "--env-file", ".env.test"})
	if err != nil {
		t.Fatalf("parseCompileArgs() error = %v", err)
	}
	if specPath != "spec.yaml" || output != "tests/spec.jmx" || envFile != ".env.test" {
		t.Fatalf("unexpected args: spec=%q output=%q env=%q", specPath, output, envFile)
	}
}

func TestRunVersion(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"version"}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("Run(version) code=%d stderr=%s", code, stderr.String())
	}
	if !strings.Contains(stdout.String(), "Loadwright") {
		t.Fatalf("version output = %q", stdout.String())
	}
}

func TestParseCompileArgsErrors(t *testing.T) {
	if _, _, _, err := parseCompileArgs([]string{"spec.yaml", "-o"}); err == nil {
		t.Fatalf("expected missing output value error")
	}
	if _, _, _, err := parseCompileArgs([]string{}); err == nil {
		t.Fatalf("expected missing spec error")
	}
}

func TestParseRunArgsAcceptsInterspersedFlags(t *testing.T) {
	input, outputDir, envFile, ci, image, err := parseRunArgs([]string{"spec.yaml", "--ci", "--out-dir=results/test", "--env-file=.env.test", "--image", "jmeter:test"})
	if err != nil {
		t.Fatalf("parseRunArgs() error = %v", err)
	}
	if input != "spec.yaml" || outputDir != "results/test" || envFile != ".env.test" || !ci || image != "jmeter:test" {
		t.Fatalf("unexpected args: input=%q outputDir=%q env=%q ci=%v image=%q", input, outputDir, envFile, ci, image)
	}
}

func TestParseRunArgsErrors(t *testing.T) {
	if _, _, _, _, _, err := parseRunArgs([]string{"spec.yaml", "--out-dir"}); err == nil {
		t.Fatalf("expected missing out-dir value error")
	}
	if _, _, _, _, _, err := parseRunArgs([]string{"spec.yaml", "--image"}); err == nil {
		t.Fatalf("expected missing image value error")
	}
	if _, _, _, _, _, err := parseRunArgs([]string{}); err == nil {
		t.Fatalf("expected missing input error")
	}
}

func TestParseDoctorArgs(t *testing.T) {
	deep, image, err := parseDoctorArgs([]string{"--deep", "--image=custom:jmeter"})
	if err != nil {
		t.Fatalf("parseDoctorArgs() error = %v", err)
	}
	if !deep || image != "custom:jmeter" {
		t.Fatalf("unexpected args: deep=%v image=%q", deep, image)
	}
}

func TestParseDoctorArgsRejectsUnknown(t *testing.T) {
	if _, _, err := parseDoctorArgs([]string{"--unknown"}); err == nil {
		t.Fatalf("expected unknown doctor option error")
	}
}

func TestParseImportOpenAPIArgs(t *testing.T) {
	input, output, baseURL, err := parseImportOpenAPIArgs([]string{"openapi.yaml", "-o", "loadwright.yaml", "--base-url=https://staging.example.com"})
	if err != nil {
		t.Fatalf("parseImportOpenAPIArgs() error = %v", err)
	}
	if input != "openapi.yaml" || output != "loadwright.yaml" || baseURL != "https://staging.example.com" {
		t.Fatalf("unexpected args: input=%q output=%q baseURL=%q", input, output, baseURL)
	}
}

func TestParseImportOpenAPIArgsErrors(t *testing.T) {
	if _, _, _, err := parseImportOpenAPIArgs([]string{"openapi.yaml", "--base-url"}); err == nil {
		t.Fatalf("expected missing base-url value error")
	}
	if _, _, _, err := parseImportOpenAPIArgs([]string{}); err == nil {
		t.Fatalf("expected missing OpenAPI input error")
	}
}

func TestRunInitCreatesStarterSpec(t *testing.T) {
	dir := t.TempDir()
	chdir(t, dir)
	var stdout, stderr bytes.Buffer
	code := Run([]string{"init"}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("Run(init) code=%d stderr=%s", code, stderr.String())
	}
	data, err := os.ReadFile(filepath.Join(dir, "loadwright.yaml"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "name: example-api") {
		t.Fatalf("unexpected starter spec: %s", data)
	}
}

func TestRunCompileCreatesJMX(t *testing.T) {
	dir := t.TempDir()
	chdir(t, dir)
	specPath := filepath.Join(dir, "spec.yaml")
	specYAML := `name: compile-me
target: https://example.com
requests:
  - path: /health
`
	if err := os.WriteFile(specPath, []byte(specYAML), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"compile", specPath, "-o", "out/test.jmx"}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("Run(compile) code=%d stderr=%s", code, stderr.String())
	}
	data, err := os.ReadFile(filepath.Join(dir, "out", "test.jmx"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), `testname="compile-me"`) {
		t.Fatalf("unexpected JMX: %s", data)
	}
}

func TestRunCompileUsesEnvFile(t *testing.T) {
	dir := t.TempDir()
	chdir(t, dir)
	specPath := filepath.Join(dir, "spec.yaml")
	envPath := filepath.Join(dir, ".env.test")
	specYAML := `name: env-compile
target: https://example.com
variables:
  token: ${API_TOKEN}
auth:
  type: bearer
  token: "{{token}}"
requests:
  - path: /secure
`
	if err := os.WriteFile(specPath, []byte(specYAML), 0o644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(envPath, []byte("API_TOKEN=abc123\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"compile", specPath, "--env-file", envPath, "-o", "out/test.jmx"}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("Run(compile) code=%d stderr=%s", code, stderr.String())
	}
	data, err := os.ReadFile(filepath.Join(dir, "out", "test.jmx"))
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "Bearer abc123") {
		t.Fatalf("compiled JMX missing resolved bearer token: %s", data)
	}
}

func TestRunImportOpenAPICreatesSpec(t *testing.T) {
	dir := t.TempDir()
	chdir(t, dir)
	openAPI := `openapi: 3.0.3
info:
  title: Import Test
servers:
  - url: https://api.example.com
paths:
  /health:
    get:
      responses:
        "200": {}
`
	if err := os.WriteFile("openapi.yaml", []byte(openAPI), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"import", "openapi", "openapi.yaml", "-o", "loadwright.yaml"}, &stdout, &stderr)
	if code != 0 {
		t.Fatalf("Run(import openapi) code=%d stderr=%s", code, stderr.String())
	}
	data, err := os.ReadFile("loadwright.yaml")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(string(data), "target: https://api.example.com") {
		t.Fatalf("unexpected imported spec: %s", data)
	}
}

func TestRunImportRejectsUnsupportedSource(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"import", "postman", "collection.json"}, &stdout, &stderr)
	if code != 2 || !strings.Contains(stderr.String(), "unsupported import source") {
		t.Fatalf("code=%d stderr=%s", code, stderr.String())
	}
}

func TestRunCompileRejectsInvalidSpec(t *testing.T) {
	dir := t.TempDir()
	chdir(t, dir)
	if err := os.WriteFile("bad.yaml", []byte("name: bad\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	var stdout, stderr bytes.Buffer
	code := Run([]string{"compile", "bad.yaml"}, &stdout, &stderr)
	if code != 1 || !strings.Contains(stderr.String(), "invalid spec") {
		t.Fatalf("code=%d stderr=%s", code, stderr.String())
	}
}

func chdir(t *testing.T, dir string) {
	t.Helper()
	previous, err := os.Getwd()
	if err != nil {
		t.Fatal(err)
	}
	if err := os.Chdir(dir); err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() {
		if err := os.Chdir(previous); err != nil {
			t.Fatalf("restore working directory: %v", err)
		}
	})
}

func TestRunRejectsUnknownCommand(t *testing.T) {
	var stdout, stderr bytes.Buffer
	code := Run([]string{"wat"}, &stdout, &stderr)
	if code != 2 || !strings.Contains(stderr.String(), "unknown command") {
		t.Fatalf("code=%d stderr=%s", code, stderr.String())
	}
}
