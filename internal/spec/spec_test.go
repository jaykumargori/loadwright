package spec

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

func TestSpecDefaultsAndDurations(t *testing.T) {
	raw := Spec{
		Name:   "smoke",
		Target: "https://example.com/",
		Load: Load{
			Users:  3,
			RampUp: Duration{Seconds: 30, Set: true},
		},
		Requests: []Request{{Path: "/health"}},
	}

	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	if raw.Target != "https://example.com" {
		t.Fatalf("target = %q", raw.Target)
	}
	if raw.Requests[0].Method != "GET" {
		t.Fatalf("method = %q", raw.Requests[0].Method)
	}
	if raw.Load.Loops == nil || *raw.Load.Loops != 1 {
		t.Fatalf("expected default loops = 1")
	}
}

func TestParseDuration(t *testing.T) {
	tests := map[any]int{
		"30s": 30,
		"2m":  120,
		"1h":  3600,
		45:    45,
	}
	for input, want := range tests {
		got, err := ParseDuration(input)
		if err != nil {
			t.Fatalf("ParseDuration(%v) error = %v", input, err)
		}
		if got != want {
			t.Fatalf("ParseDuration(%v) = %d, want %d", input, got, want)
		}
	}
}

func TestSpecRejectsBadTarget(t *testing.T) {
	raw := Spec{
		Name:     "bad",
		Target:   "ftp://example.com",
		Requests: []Request{{Path: "/health"}},
	}
	if err := raw.NormalizeAndValidate(); err == nil {
		t.Fatalf("expected invalid target error")
	}
}

func TestDurationLoadDefaultsToInfiniteLoops(t *testing.T) {
	raw := Spec{
		Name:   "duration",
		Target: "https://example.com",
		Load: Load{
			Users:    4,
			Duration: Duration{Seconds: 120, Set: true},
		},
		Requests: []Request{{Path: "/health"}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	if raw.Load.Loops != nil {
		t.Fatalf("duration-based loads should not default loops")
	}
}

func TestRequestValidationScenarios(t *testing.T) {
	tests := []struct {
		name    string
		request Request
		want    string
	}{
		{
			name:    "bad path",
			request: Request{Method: "GET", Path: "health"},
			want:    "path must start with /",
		},
		{
			name:    "bad method",
			request: Request{Method: "TRACE", Path: "/health"},
			want:    "method is not supported",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.request.NormalizeAndValidate(0)
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Fatalf("error = %v, want substring %q", err, tt.want)
			}
		})
	}
}

func TestLoadFileParsesThresholdsAndRequestShape(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, "spec.yaml")
	yaml := `name: parse-me
target: https://example.com
load:
  users: 2
  ramp_up: 5s
requests:
  - method: POST
    path: /submit
    headers:
      content-type: application/json
    query:
      trace: "true"
    body:
      ok: true
    expect:
      status: 201
thresholds:
  error_rate_lt: 1
  p95_ms_lt: 500
`
	if err := os.WriteFile(path, []byte(yaml), 0o644); err != nil {
		t.Fatal(err)
	}
	loaded, err := LoadFile(path)
	if err != nil {
		t.Fatalf("LoadFile() error = %v", err)
	}
	if loaded.Load.RampUp.Seconds != 5 || loaded.Requests[0].Expect.Status != 201 {
		t.Fatalf("unexpected loaded spec: %+v", loaded)
	}
	if loaded.Thresholds.ErrorRateLT == nil || *loaded.Thresholds.ErrorRateLT != 1 {
		t.Fatalf("threshold not parsed: %+v", loaded.Thresholds)
	}
}
