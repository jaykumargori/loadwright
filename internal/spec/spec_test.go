package spec

import "testing"

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
