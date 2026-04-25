package jmx

import (
	"encoding/xml"
	"strings"
	"testing"

	"github.com/jmeterx/jmeterx/internal/spec"
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
