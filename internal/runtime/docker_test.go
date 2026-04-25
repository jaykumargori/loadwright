package runtime

import (
	"path/filepath"
	"strings"
	"testing"
)

func TestFirstVersionLine(t *testing.T) {
	tests := []struct {
		name   string
		output string
		want   string
	}{
		{
			name:   "plain apache version",
			output: "Apache JMeter 5.6.3\n",
			want:   "Apache JMeter 5.6.3",
		},
		{
			name:   "ascii art version",
			output: "/_/   \\_\\_| /_/   \\_\\____|_| |_|_____|  \\___/|_|  |_|_____| |_| |_____|_| \\_\\ 5.5\n",
			want:   "Apache JMeter 5.5",
		},
		{
			name:   "no version",
			output: "hello\n",
			want:   "",
		},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := firstVersionLine(tt.output); got != tt.want {
				t.Fatalf("firstVersionLine() = %q, want %q", got, tt.want)
			}
		})
	}
}

func TestStringTrim(t *testing.T) {
	if got := stringTrim([]byte(" server \r\n")); got != " server" {
		t.Fatalf("stringTrim() = %q", got)
	}
}

func TestMustRel(t *testing.T) {
	base := t.TempDir()
	target := filepath.Join(base, "results")
	if got := mustRel(base, target); got != "results" {
		t.Fatalf("mustRel() = %q", got)
	}
}

func TestCheckWritableDir(t *testing.T) {
	dir := filepath.Join(t.TempDir(), "nested")
	check := checkWritableDir(dir, "nested")
	if !check.Passed || !strings.Contains(check.Message, "writable") {
		t.Fatalf("unexpected check: %+v", check)
	}
}
