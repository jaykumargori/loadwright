package cli

import (
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/devaryakjha/loadwright/internal/jmx"
	"github.com/devaryakjha/loadwright/internal/openapi"
	"github.com/devaryakjha/loadwright/internal/report"
	"github.com/devaryakjha/loadwright/internal/runtime"
	"github.com/devaryakjha/loadwright/internal/spec"
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
		return doctor(args[1:], stdout, stderr)
	case "init":
		return initSpec(args[1:], stdout, stderr)
	case "compile":
		return compile(args[1:], stdout, stderr)
	case "run":
		return run(args[1:], stdout, stderr)
	case "import":
		return importCommand(args[1:], stdout, stderr)
	default:
		fmt.Fprintf(stderr, "unknown command: %s\n\n", args[0])
		usage(stderr)
		return 2
	}
}

func usage(w io.Writer) {
	fmt.Fprintln(w, `Loadwright: Docker-first, spec-driven JMeter automation

Usage:
  loadwright doctor [--deep] [--image justb4/jmeter:latest]
  loadwright init [path]
  loadwright import openapi <openapi.yaml|openapi.json> [-o loadwright.yaml] [--base-url https://api.example.com]
  loadwright compile <spec.yaml> [-o tests/name.jmx] [--env-file .env.test]
  loadwright run <spec.yaml|test.jmx> [--out-dir results/run] [--env-file .env.test] [--ci]

Commands:
  doctor    Check local Docker/JMeter prerequisites
  init      Write a starter YAML spec
  import    Convert supported source formats to Loadwright specs
  compile   Compile a YAML spec to JMeter JMX
  run       Run a YAML spec or existing JMX through Dockerized JMeter`)
}

func doctor(args []string, stdout io.Writer, stderr io.Writer) int {
	deep, image, err := parseDoctorArgs(args)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	failed := false
	for _, check := range runtime.Doctor(runtime.DoctorOptions{Deep: deep, Image: image}) {
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

func parseDoctorArgs(args []string) (deep bool, image string, err error) {
	image = runtime.DefaultJMeterImage
	for i := 0; i < len(args); i++ {
		arg := args[i]
		switch {
		case arg == "--deep":
			deep = true
		case arg == "--image":
			i++
			if i >= len(args) {
				return false, "", fmt.Errorf("%s requires a value", arg)
			}
			image = args[i]
		case strings.HasPrefix(arg, "--image="):
			image = strings.TrimPrefix(arg, "--image=")
		default:
			return false, "", fmt.Errorf("unknown doctor option: %s", arg)
		}
	}
	return deep, image, nil
}

func initSpec(args []string, stdout io.Writer, stderr io.Writer) int {
	path := "loadwright.yaml"
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
	specPath, output, envFile, err := parseCompileArgs(args)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	loaded, err := loadResolvedSpec(specPath, envFile)
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
	input, outputDir, envFile, ci, image, err := parseRunArgs(args)
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
		loaded, err := loadResolvedSpec(input, envFile)
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

func importCommand(args []string, stdout io.Writer, stderr io.Writer) int {
	if len(args) == 0 {
		fmt.Fprintln(stderr, "import requires a source type")
		return 2
	}
	switch args[0] {
	case "openapi":
		return importOpenAPI(args[1:], stdout, stderr)
	default:
		fmt.Fprintf(stderr, "unsupported import source: %s\n", args[0])
		return 2
	}
}

func importOpenAPI(args []string, stdout io.Writer, stderr io.Writer) int {
	input, output, baseURL, err := parseImportOpenAPIArgs(args)
	if err != nil {
		fmt.Fprintln(stderr, err)
		return 2
	}
	imported, err := openapi.ImportFile(input, openapi.Options{BaseURL: baseURL})
	if err != nil {
		fmt.Fprintf(stderr, "import failed: %v\n", err)
		return 1
	}
	if output == "" {
		output = "loadwright.yaml"
	}
	if err := spec.WriteFile(imported, output); err != nil {
		fmt.Fprintf(stderr, "write spec failed: %v\n", err)
		return 1
	}
	fmt.Fprintf(stdout, "wrote %s\n", output)
	return 0
}

func loadResolvedSpec(path string, envFile string) (*spec.Spec, error) {
	env, err := spec.LoadEnvFile(envFile)
	if err != nil {
		return nil, err
	}
	loaded, err := spec.LoadFileUnresolved(path)
	if err != nil {
		return nil, err
	}
	return loaded.Resolve(env, spec.WithBaseDir(filepath.Dir(path)))
}

func parseCompileArgs(args []string) (specPath string, output string, envFile string, err error) {
	var positional []string
	for i := 0; i < len(args); i++ {
		arg := args[i]
		switch {
		case arg == "-o" || arg == "--out":
			i++
			if i >= len(args) {
				return "", "", "", fmt.Errorf("%s requires a value", arg)
			}
			output = args[i]
		case strings.HasPrefix(arg, "-o="):
			output = strings.TrimPrefix(arg, "-o=")
		case strings.HasPrefix(arg, "--out="):
			output = strings.TrimPrefix(arg, "--out=")
		case arg == "--env-file":
			i++
			if i >= len(args) {
				return "", "", "", fmt.Errorf("%s requires a value", arg)
			}
			envFile = args[i]
		case strings.HasPrefix(arg, "--env-file="):
			envFile = strings.TrimPrefix(arg, "--env-file=")
		default:
			positional = append(positional, arg)
		}
	}
	if len(positional) != 1 {
		return "", "", "", fmt.Errorf("compile requires exactly one spec path")
	}
	return positional[0], output, envFile, nil
}

func parseRunArgs(args []string) (input string, outputDir string, envFile string, ci bool, image string, err error) {
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
				return "", "", "", false, "", fmt.Errorf("%s requires a value", arg)
			}
			outputDir = args[i]
		case strings.HasPrefix(arg, "--out-dir="):
			outputDir = strings.TrimPrefix(arg, "--out-dir=")
		case arg == "--image":
			i++
			if i >= len(args) {
				return "", "", "", false, "", fmt.Errorf("%s requires a value", arg)
			}
			image = args[i]
		case strings.HasPrefix(arg, "--image="):
			image = strings.TrimPrefix(arg, "--image=")
		case arg == "--env-file":
			i++
			if i >= len(args) {
				return "", "", "", false, "", fmt.Errorf("%s requires a value", arg)
			}
			envFile = args[i]
		case strings.HasPrefix(arg, "--env-file="):
			envFile = strings.TrimPrefix(arg, "--env-file=")
		default:
			positional = append(positional, arg)
		}
	}
	if len(positional) != 1 {
		return "", "", "", false, "", fmt.Errorf("run requires exactly one spec or JMX path")
	}
	return positional[0], outputDir, envFile, ci, image, nil
}

func parseImportOpenAPIArgs(args []string) (input string, output string, baseURL string, err error) {
	var positional []string
	for i := 0; i < len(args); i++ {
		arg := args[i]
		switch {
		case arg == "-o" || arg == "--out":
			i++
			if i >= len(args) {
				return "", "", "", fmt.Errorf("%s requires a value", arg)
			}
			output = args[i]
		case strings.HasPrefix(arg, "-o="):
			output = strings.TrimPrefix(arg, "-o=")
		case strings.HasPrefix(arg, "--out="):
			output = strings.TrimPrefix(arg, "--out=")
		case arg == "--base-url":
			i++
			if i >= len(args) {
				return "", "", "", fmt.Errorf("%s requires a value", arg)
			}
			baseURL = args[i]
		case strings.HasPrefix(arg, "--base-url="):
			baseURL = strings.TrimPrefix(arg, "--base-url=")
		default:
			positional = append(positional, arg)
		}
	}
	if len(positional) != 1 {
		return "", "", "", fmt.Errorf("import openapi requires exactly one input file")
	}
	return positional[0], output, baseURL, nil
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
