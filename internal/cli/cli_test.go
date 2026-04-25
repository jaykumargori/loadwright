package cli

import "testing"

func TestParseCompileArgsAcceptsFlagsAfterSpec(t *testing.T) {
	specPath, output, err := parseCompileArgs([]string{"spec.yaml", "-o", "tests/spec.jmx"})
	if err != nil {
		t.Fatalf("parseCompileArgs() error = %v", err)
	}
	if specPath != "spec.yaml" || output != "tests/spec.jmx" {
		t.Fatalf("unexpected args: spec=%q output=%q", specPath, output)
	}
}

func TestParseRunArgsAcceptsInterspersedFlags(t *testing.T) {
	input, outputDir, ci, image, err := parseRunArgs([]string{"spec.yaml", "--ci", "--out-dir=results/test", "--image", "jmeter:test"})
	if err != nil {
		t.Fatalf("parseRunArgs() error = %v", err)
	}
	if input != "spec.yaml" || outputDir != "results/test" || !ci || image != "jmeter:test" {
		t.Fatalf("unexpected args: input=%q outputDir=%q ci=%v image=%q", input, outputDir, ci, image)
	}
}
