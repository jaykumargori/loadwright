package cli

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/jmeterx/jmeterx/internal/jmx"
	"github.com/jmeterx/jmeterx/internal/report"
	"github.com/jmeterx/jmeterx/internal/runtime"
	"github.com/jmeterx/jmeterx/internal/spec"
)

func Run(args []string, stdout io.Writer, stderr io.Writer) int {
	if len(args) == 0 {
		usage(stdout)
		return 0
	}
	switch args[0] {
	case "help", "-h", "--help":
		usage(stdout)
		return 0
	case "doctor":
		return doctor(stdout)
	case "init":
		return initSpec(args[1:], stdout, stderr)
	case "compile":
		return compile(args[1:], stdout, stderr)
	case "run":
		return run(args[1:], stdout, stderr)
	default:
		fmt.Fprintf(stderr, "unknown command: %s\n\n", args[0])
		usage(stderr)
		return 2
	}
}

func usage(w io.Writer) {
	fmt.Fprintln(w, `jmeterx: Docker-first, spec-driven JMeter automation

Usage:
  jmeterx doctor
  jmeterx init [path]
  jmeterx compile <spec.yaml> [-o tests/name.jmx]
  jmeterx run <spec.yaml|test.jmx> [--out-dir results/run] [--ci]

Commands:
  doctor    Check local Docker/JMeter prerequisites
  init      Write a starter YAML spec
  compile   Compile a YAML spec to JMeter JMX
  run       Run a YAML spec or existing JMX through Dockerized JMeter`)
}

func doctor(stdout io.Writer) int {
	failed := false
	for _, check := range runtime.Doctor() {
		status := "PASS"
		if !check.Passed {
			status = "FAIL"
			failed = true
		}
		fmt.Fprintf(stdout, "%-14s %s %s\n", status, check.Name, check.Message)
	}
	if failed {
		return 1
	}
	return 0
}

func initSpec(args []string, stdout io.Writer, stderr io.Writer) int {
	path := "jmeterx.yaml"
	if len(args) > 0 {
		path = args[0]
	}
	if _, err := os.Stat(path); err == nil {
		fmt.Fprintf(stderr, "%s already exists\n", path)
		return 1
	}
	if err := os.WriteFile(path, []byte(starterSpec), 0o644); err != nil {
		fmt.Fprintf(stderr, "write starter spec: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "created %s\n", path)
	return 0
}

func compile(args []string, stdout io.Writer, stderr io.Writer) int {
	specPath, output, err := parseCompileArgs(args)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	loaded, err := spec.LoadFile(specPath)
	if err != nil {
		fmt.Fprintf(stderr, "invalid spec: %v\n", err)
		return 1
	}
	out := output
	if out == "" {
		out = filepath.Join("tests", jmx.SafeName(loaded.Name)+".jmx")
	}
	if err := jmx.Compile(loaded, out); err != nil {
		fmt.Fprintf(stderr, "compile failed: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "wrote %s\n", out)
	return 0
}

func run(args []string, stdout io.Writer, stderr io.Writer) int {
	input, outputDir, ci, image, err := parseRunArgs(args)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	runID := time.Now().UTC().Format("20060102-150405")
	if outputDir == "" {
		outputDir = filepath.Join("results", runID)
	}
	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		fmt.Fprintf(stderr, "create output dir: %v\n", err)
		return 1
	}

	var thresholds spec.Thresholds
	jmxPath := input
	workDir := "."
	if isYAML(input) {
		loaded, err := spec.LoadFile(input)
		if err != nil {
			fmt.Fprintf(stderr, "invalid spec: %v\n", err)
			return 1
		}
		thresholds = loaded.Thresholds
		jmxPath = filepath.Join(outputDir, jmx.SafeName(loaded.Name)+".jmx")
		if err := jmx.Compile(loaded, jmxPath); err != nil {
			fmt.Fprintf(stderr, "compile failed: %v\n", err)
			return 1
		}
		workDir = outputDir
		fmt.Fprintf(stdout, "compiled %s\n", jmxPath)
	}

	jtlName := "results.jtl"
	err = runtime.RunJMeter(runtime.RunOptions{
		Image:      image,
		WorkDir:    workDir,
		JMXPath:    jmxPath,
		ResultsDir: outputDir,
		JTLName:    jtlName,
	})
	if err != nil {
		fmt.Fprintf(stderr, "jmeter run failed: %v\n", err)
		return 1
	}

	summary, err := report.ParseJTL(filepath.Join(outputDir, jtlName), thresholds)
	if err != nil {
		fmt.Fprintf(stderr, "parse report failed: %v\n", err)
		return 1
	}
	if err := report.WriteAll(summary, outputDir); err != nil {
		fmt.Fprintf(stderr, "write report failed: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "report %s\n", filepath.Join(outputDir, "index.html"))
	if ci && !summary.Passed() {
		fmt.Fprintln(stderr, "thresholds failed")
		return 1
	}
	return 0
}

func parseCompileArgs(args []string) (specPath string, output string, err error) {
	var positional []string
	for i := 0; i < len(args); i++ {
		arg := args[i]
		switch {
		case arg == "-o" || arg == "--out":
			i++
			if i >= len(args) {
				return "", "", fmt.Errorf("%s requires a value", arg)
			}
			output = args[i]
		case strings.HasPrefix(arg, "-o="):
			output = strings.TrimPrefix(arg, "-o=")
		case strings.HasPrefix(arg, "--out="):
			output = strings.TrimPrefix(arg, "--out=")
		default:
			positional = append(positional, arg)
		}
	}
	if len(positional) != 1 {
		return "", "", fmt.Errorf("compile requires exactly one spec path")
	}
	return positional[0], output, nil
}

func parseRunArgs(args []string) (input string, outputDir string, ci bool, image string, err error) {
	image = runtime.DefaultJMeterImage
	var positional []string
	for i := 0; i < len(args); i++ {
		arg := args[i]
		switch {
		case arg == "--ci":
			ci = true
		case arg == "--out-dir":
			i++
			if i >= len(args) {
				return "", "", false, "", fmt.Errorf("%s requires a value", arg)
			}
			outputDir = args[i]
		case strings.HasPrefix(arg, "--out-dir="):
			outputDir = strings.TrimPrefix(arg, "--out-dir=")
		case arg == "--image":
			i++
			if i >= len(args) {
				return "", "", false, "", fmt.Errorf("%s requires a value", arg)
			}
			image = args[i]
		case strings.HasPrefix(arg, "--image="):
			image = strings.TrimPrefix(arg, "--image=")
		default:
			positional = append(positional, arg)
		}
	}
	if len(positional) != 1 {
		return "", "", false, "", fmt.Errorf("run requires exactly one spec or JMX path")
	}
	return positional[0], outputDir, ci, image, nil
}

func isYAML(path string) bool {
	ext := strings.ToLower(filepath.Ext(path))
	return ext == ".yaml" || ext == ".yml"
}

const starterSpec = `name: example-api
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
  - name: post payload
    method: POST
    path: /post
    headers:
      content-type: application/json
    body:
      hello: world
    expect:
      status: 200
thresholds:
  error_rate_lt: 1
  p95_ms_lt: 3000
`
