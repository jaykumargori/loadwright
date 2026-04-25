package report

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/devaryakjha/loadwright/internal/spec"
)

func TestParseJTLEvaluatesThresholds(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "results.jtl")
	jtl := `timeStamp,elapsed,label,responseCode,success
1,100,GET /health,200,true
2,200,GET /health,200,true
3,1000,POST /login,500,false
`
	if err := os.WriteFile(path, []byte(jtl), 0o644); err != nil {
		t.Fatal(err)
	}
	errorRate := 50.0
	p95 := 900.0
	summary, err := ParseJTL(path, spec.Thresholds{
		ErrorRateLT: &errorRate,
		P95MsLT:     &p95,
	})
	if err != nil {
		t.Fatalf("ParseJTL() error = %v", err)
	}
	if summary.TotalSamples != 3 || summary.Failed != 1 {
		t.Fatalf("unexpected summary: %+v", summary)
	}
	if summary.Passed() {
		t.Fatalf("expected p95 threshold to fail")
	}
}

func TestParseJTLAllSuccessPassesThresholds(t *testing.T) {
	path := writeJTL(t, `timeStamp,elapsed,label,responseCode,success
1,100,GET /health,200,true
2,200,GET /health,200,true
3,300,POST /login,200,true
`)
	errorRate := 1.0
	p95 := 500.0
	avg := 250.0
	summary, err := ParseJTL(path, spec.Thresholds{
		ErrorRateLT: &errorRate,
		P95MsLT:     &p95,
		AvgMsLT:     &avg,
	})
	if err != nil {
		t.Fatalf("ParseJTL() error = %v", err)
	}
	if !summary.Passed() {
		t.Fatalf("expected thresholds to pass: %+v", summary.Thresholds)
	}
	if len(summary.Endpoints) != 2 {
		t.Fatalf("expected two endpoints: %+v", summary.Endpoints)
	}
}

func TestParseJTLEmptyFile(t *testing.T) {
	path := writeJTL(t, "")
	summary, err := ParseJTL(path, spec.Thresholds{})
	if err != nil {
		t.Fatalf("ParseJTL() error = %v", err)
	}
	if summary.TotalSamples != 0 || len(summary.Endpoints) != 0 {
		t.Fatalf("unexpected empty summary: %+v", summary)
	}
}

func TestParseJTLMalformedCSV(t *testing.T) {
	path := writeJTL(t, "timeStamp,elapsed,label\n\"unterminated")
	if _, err := ParseJTL(path, spec.Thresholds{}); err == nil {
		t.Fatalf("expected malformed CSV error")
	}
}

func TestRenderOutputsContainThresholdStatus(t *testing.T) {
	summary := &Summary{
		TotalSamples: 2,
		Successful:   2,
		AverageMS:    100,
		P95MS:        150,
		Thresholds: []ThresholdResult{{
			Name:   "p95_ms_lt",
			Limit:  200,
			Actual: 150,
			Passed: true,
		}},
	}
	if got := RenderMarkdown(summary); !strings.Contains(got, "p95_ms_lt: PASS") {
		t.Fatalf("markdown missing threshold pass: %s", got)
	}
	if got := RenderHTML(summary); !strings.Contains(got, "p95_ms_lt") || !strings.Contains(got, "PASS") {
		t.Fatalf("html missing threshold table: %s", got)
	}
}

func TestWriteAllCreatesArtifacts(t *testing.T) {
	dir := t.TempDir()
	summary := &Summary{TotalSamples: 1, Successful: 1, Endpoints: map[string]Endpoint{}}
	if err := WriteAll(summary, dir); err != nil {
		t.Fatalf("WriteAll() error = %v", err)
	}
	for _, name := range []string{"summary.json", "summary.md", "index.html"} {
		if _, err := os.Stat(filepath.Join(dir, name)); err != nil {
			t.Fatalf("expected %s: %v", name, err)
		}
	}
}

func writeJTL(t *testing.T, contents string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, "results.jtl")
	if err := os.WriteFile(path, []byte(contents), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}
