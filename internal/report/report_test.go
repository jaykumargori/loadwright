package report

import (
	"os"
	"path/filepath"
	"testing"

	"github.com/jmeterx/jmeterx/internal/spec"
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
