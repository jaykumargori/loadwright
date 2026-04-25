package jmx

import (
	"crypto/sha256"
	"encoding/xml"
	"fmt"
	"strings"
	"testing"

	"github.com/devaryakjha/loadwright/internal/spec"
)

func TestRenderProducesValidJMX(t *testing.T) {
	loops := 2
	loaded := &spec.Spec{
		Name:   "api smoke",
		Target: "https://example.com",
		Load: spec.Load{
			Users:  5,
			RampUp: spec.Duration{Seconds: 10, Set: true},
			Loops:  &loops,
		},
		Requests: []spec.Request{
			{
				Name:    "GET health",
				Method:  "GET",
				Path:    "/health",
				Headers: map[string]string{"accept": "application/json"},
				Expect:  spec.Expect{Status: 200},
			},
		},
	}

	rendered := Render(loaded)
	var root struct {
		XMLName xml.Name
	}
	if err := xml.Unmarshal([]byte(rendered), &root); err != nil {
		t.Fatalf("rendered JMX is not XML: %v\n%s", err, rendered)
	}
	for _, expected := range []string{
		`testname="api smoke"`,
		`<stringProp name="HTTPSampler.domain">example.com</stringProp>`,
		`<stringProp name="HTTPSampler.path">/health</stringProp>`,
		`<stringProp name="Header.name">accept</stringProp>`,
		`<stringProp name="Assertion.test_field">Assertion.response_code</stringProp>`,
	} {
		if !strings.Contains(rendered, expected) {
			t.Fatalf("rendered JMX missing %q\n%s", expected, rendered)
		}
	}
}

func TestExampleGoldenHash(t *testing.T) {
	loops := 3
	loaded := &spec.Spec{
		Name:   "httpbin-basic",
		Target: "https://httpbin.org",
		Load: spec.Load{
			Users:  5,
			RampUp: spec.Duration{Seconds: 10, Set: true},
			Loops:  &loops,
		},
		Requests: []spec.Request{
			{
				Name:   "get status",
				Method: "GET",
				Path:   "/status/200",
				Expect: spec.Expect{Status: 200},
			},
			{
				Name:    "post json",
				Method:  "POST",
				Path:    "/post",
				Headers: map[string]string{"content-type": "application/json"},
				Body: map[string]any{
					"kind":   "example",
					"source": "Loadwright",
				},
				Expect: spec.Expect{Status: 200},
			},
		},
	}

	hash := sha256.Sum256([]byte(Render(loaded)))
	got := fmt.Sprintf("%x", hash)
	const want = "991b2afee60b1b676317415750e2625db7a6bc52469db0d3e63f4099a5f0d94e"
	if got != want {
		t.Fatalf("JMX golden hash changed: got %s, want %s", got, want)
	}
}
