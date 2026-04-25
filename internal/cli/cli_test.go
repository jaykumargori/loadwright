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

func TestParseRunArgsAcceptsInterspersedFlags(t *testing.T) {
	input, outputDir, envFile, ci, image, err := parseRunArgs([]string{"spec.yaml", "--ci", "--out-dir=results/test", "--env-file=.env.test", "--image", "jmeter:test"})
	if err != nil {
		t.Fatalf("parseRunArgs() error = %v", err)
	}
	if input != "spec.yaml" || outputDir != "results/test" || envFile != ".env.test" || !ci || image != "jmeter:test" {
		t.Fatalf("unexpected args: input=%q outputDir=%q env=%q ci=%v image=%q", input, outputDir, envFile, ci, image)
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
