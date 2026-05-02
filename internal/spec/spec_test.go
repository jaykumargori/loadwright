package spec

import (
	"gopkg.in/yaml.v3"
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

func TestParseDurationRejectsInvalidValues(t *testing.T) {
	for _, input := range []any{"", "soon", 0, -1, []string{"1s"}} {
		if _, err := ParseDuration(input); err == nil {
			t.Fatalf("expected ParseDuration(%v) to fail", input)
		}
	}
}

func TestDurationMarshalYAML(t *testing.T) {
	data, err := yaml.Marshal(Duration{Seconds: 7, Set: true})
	if err != nil {
		t.Fatalf("Marshal() error = %v", err)
	}
	if strings.TrimSpace(string(data)) != "7s" {
		t.Fatalf("duration YAML = %q", data)
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

func TestSpecValidationFailures(t *testing.T) {
	tests := []struct {
		name string
		spec Spec
		want string
	}{
		{name: "missing name", spec: Spec{Target: "https://example.com", Requests: []Request{{Path: "/x"}}}, want: "name is required"},
		{name: "bad users", spec: Spec{Name: "bad", Target: "https://example.com", Load: Load{Users: -1}, Requests: []Request{{Path: "/x"}}}, want: "load.users"},
		{name: "bad loops", spec: Spec{Name: "bad", Target: "https://example.com", Load: Load{Loops: intPtr(0)}, Requests: []Request{{Path: "/x"}}}, want: "load.loops"},
		{name: "no requests", spec: Spec{Name: "bad", Target: "https://example.com"}, want: "requests"},
		{name: "bad auth", spec: Spec{Name: "bad", Target: "https://example.com", Auth: Auth{Type: "bearer"}, Requests: []Request{{Path: "/x"}}}, want: "auth.token"},
		{name: "bad protocol", spec: Spec{Name: "bad", Target: "https://example.com", Requests: []Request{{Protocol: "gopher", Path: "/x"}}}, want: "protocol is not supported"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.spec.NormalizeAndValidate()
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Fatalf("error = %v, want substring %q", err, tt.want)
			}
		})
	}
}

func TestSpecValidationCollectsMultipleFailures(t *testing.T) {
	loops := 0
	raw := Spec{
		Load: Load{Users: -1, Loops: &loops},
		Requests: []Request{
			{Method: "TRACE", Path: "missing-leading-slash"},
			{Path: "/ok"},
		},
	}
	err := raw.NormalizeAndValidate()
	if err == nil {
		t.Fatalf("expected validation error")
	}
	for _, want := range []string{
		"name is required",
		"target must be an absolute http, https, ws, or wss URL",
		"load.users must be greater than 0",
		"load.loops must be greater than 0",
		"requests[0].method is not supported: TRACE",
	} {
		if !strings.Contains(err.Error(), want) {
			t.Fatalf("error = %v, want substring %q", err, want)
		}
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
		{
			name:    "websocket with invalid url",
			request: Request{Protocol: "websocket", WebSocket: WebSocket{URL: "http://example.com"}},
			want:    "websocket.url must use ws or wss",
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

func TestWebSocketRequestValidationAndDefaults(t *testing.T) {
	raw := Spec{
		Name:   "ws",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			Path:     "/chat",
			Timeout:  Duration{Seconds: 4, Set: true},
			WebSocket: WebSocket{
				Message:        "ping",
				ExpectContains: "pong",
			},
		}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	request := raw.Requests[0]
	if request.Protocol != "websocket" {
		t.Fatalf("protocol = %q", request.Protocol)
	}
	if request.Name != "WS /chat" {
		t.Fatalf("name = %q", request.Name)
	}
	if request.WebSocket.Timeout.Seconds != 4 {
		t.Fatalf("timeout was not propagated: %+v", request.WebSocket.Timeout)
	}
}

func TestWebSocketRequestRejectsHTTPFields(t *testing.T) {
	request := Request{
		Protocol: "websocket",
		Path:     "/chat",
		Headers:  map[string]string{"x-test": "1"},
	}
	err := request.NormalizeAndValidate(0)
	if err == nil || !strings.Contains(err.Error(), "websocket requests only support websocket.* fields") {
		t.Fatalf("error = %v", err)
	}
}

func TestWebSocketRequestRequiresURLWhenTargetIsHTTP(t *testing.T) {
	raw := Spec{
		Name:   "ws-on-http-target",
		Target: "https://example.com",
		Requests: []Request{{
			Protocol: "websocket",
			Path:     "/socket",
		}},
	}
	err := raw.NormalizeAndValidate()
	if err == nil || !strings.Contains(err.Error(), "websocket.url is required when target is not ws or wss") {
		t.Fatalf("error = %v", err)
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

func TestResolveVariablesEnvAndBearerAuth(t *testing.T) {
	raw := Spec{
		Name:   "{{service}} smoke",
		Target: "https://{{host}}",
		Variables: map[string]string{
			"service": "checkout",
			"host":    "${API_HOST}",
			"token":   "${API_TOKEN}",
		},
		Auth: Auth{Type: "bearer", Token: "{{token}}"},
		Requests: []Request{{
			Path: "/{{service}}/health",
			Body: map[string]any{"service": "{{service}}"},
		}},
	}
	resolved, err := raw.Resolve(map[string]string{"API_HOST": "api.example.com", "API_TOKEN": "secret"})
	if err != nil {
		t.Fatalf("Resolve() error = %v", err)
	}
	if resolved.Name != "checkout smoke" || resolved.Target != "https://api.example.com" {
		t.Fatalf("unexpected resolved spec: %+v", resolved)
	}
	if resolved.Requests[0].Path != "/checkout/health" {
		t.Fatalf("path = %q", resolved.Requests[0].Path)
	}
	if got := resolved.Requests[0].Headers["Authorization"]; got != "Bearer secret" {
		t.Fatalf("authorization = %q", got)
	}
	body := resolved.Requests[0].Body.(map[string]any)
	if body["service"] != "checkout" {
		t.Fatalf("body not resolved: %+v", body)
	}
}

func TestResolvePreservesJMeterRuntimeVariables(t *testing.T) {
	raw := Spec{
		Name:   "csv",
		Target: "https://example.com",
		Requests: []Request{{
			Path: "/login",
			Body: map[string]any{
				"username": "${username}",
			},
		}},
	}
	resolved, err := raw.Resolve(nil)
	if err != nil {
		t.Fatalf("Resolve() error = %v", err)
	}
	body := resolved.Requests[0].Body.(map[string]any)
	if body["username"] != "${username}" {
		t.Fatalf("runtime variable was not preserved: %+v", body)
	}
}

func TestResolveBasicAuthAndExistingAuthorizationHeader(t *testing.T) {
	raw := Spec{
		Name:   "basic",
		Target: "https://example.com",
		Auth:   Auth{Type: "basic", Username: "user", Password: "pass"},
		Requests: []Request{
			{Path: "/basic"},
			{Path: "/custom", Headers: map[string]string{"authorization": "Bearer custom"}},
		},
	}
	resolved, err := raw.Resolve(nil)
	if err != nil {
		t.Fatalf("Resolve() error = %v", err)
	}
	if got := resolved.Requests[0].Headers["Authorization"]; got != "Basic dXNlcjpwYXNz" {
		t.Fatalf("basic auth = %q", got)
	}
	if got := resolved.Requests[1].Headers["authorization"]; got != "Bearer custom" {
		t.Fatalf("custom auth overwritten: %q", got)
	}
}

func TestResolveMissingVariableErrors(t *testing.T) {
	raw := Spec{
		Name:     "missing",
		Target:   "https://example.com",
		Requests: []Request{{Path: "/{{missing}}"}},
	}
	_, err := raw.Resolve(nil)
	if err == nil || !strings.Contains(err.Error(), "missing variable") {
		t.Fatalf("Resolve() error = %v", err)
	}
}

func TestResolveMissingEnvErrors(t *testing.T) {
	raw := Spec{
		Name:   "missing env",
		Target: "https://example.com",
		Variables: map[string]string{
			"token": "${DOES_NOT_EXIST_FOR_LOADWRIGHT_TEST}",
		},
		Requests: []Request{{Path: "/x"}},
	}
	_, err := raw.Resolve(nil)
	if err == nil || !strings.Contains(err.Error(), "missing environment value") {
		t.Fatalf("Resolve() error = %v", err)
	}
}

func TestLoadEnvFile(t *testing.T) {
	dir := t.TempDir()
	path := filepath.Join(dir, ".env")
	contents := `# comment
API_TOKEN="quoted"
export API_HOST=api.example.com
`
	if err := os.WriteFile(path, []byte(contents), 0o644); err != nil {
		t.Fatal(err)
	}
	values, err := LoadEnvFile(path)
	if err != nil {
		t.Fatalf("LoadEnvFile() error = %v", err)
	}
	if values["API_TOKEN"] != "quoted" || values["API_HOST"] != "api.example.com" {
		t.Fatalf("unexpected env values: %+v", values)
	}
}

func TestLoadEnvFileRejectsBadLine(t *testing.T) {
	path := filepath.Join(t.TempDir(), ".env")
	if err := os.WriteFile(path, []byte("NOT_VALID\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	if _, err := LoadEnvFile(path); err == nil {
		t.Fatalf("expected invalid env file error")
	}
}

func TestWriteFileRoundTrip(t *testing.T) {
	path := filepath.Join(t.TempDir(), "nested", "loadwright.yaml")
	original := &Spec{
		Name:     "write-me",
		Target:   "https://example.com",
		Requests: []Request{{Path: "/health"}},
	}
	if err := WriteFile(original, path); err != nil {
		t.Fatalf("WriteFile() error = %v", err)
	}
	loaded, err := LoadFile(path)
	if err != nil {
		t.Fatalf("LoadFile() error = %v", err)
	}
	if loaded.Name != "write-me" || loaded.Target != "https://example.com" {
		t.Fatalf("unexpected roundtrip: %+v", loaded)
	}
}

func TestDefaultTimeoutAppliesToRequests(t *testing.T) {
	raw := Spec{
		Name:     "timeouts",
		Target:   "https://example.com",
		Defaults: Defaults{Timeout: Duration{Seconds: 5, Set: true}},
		Requests: []Request{
			{Path: "/default"},
			{Path: "/override", Timeout: Duration{Seconds: 2, Set: true}},
		},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	if raw.Requests[0].Timeout.Seconds != 5 || raw.Requests[1].Timeout.Seconds != 2 {
		t.Fatalf("unexpected timeouts: %+v", raw.Requests)
	}
}

func TestDataSetInfersCSVHeader(t *testing.T) {
	dir := t.TempDir()
	csvPath := filepath.Join(dir, "users.csv")
	if err := os.WriteFile(csvPath, []byte("username,password\nalice,secret\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	raw := Spec{
		Name:   "csv",
		Target: "https://example.com",
		Data: map[string]DataSet{
			"users": {File: "users.csv"},
		},
		Requests: []Request{{Path: "/login"}},
	}
	if err := raw.NormalizeAndValidate(WithBaseDir(dir)); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	got := strings.Join(raw.Data["users"].Variables, ",")
	if got != "username,password" {
		t.Fatalf("variables = %q", got)
	}
	if raw.Data["users"].Sharing != "all" {
		t.Fatalf("sharing = %q", raw.Data["users"].Sharing)
	}
}

func TestDataSetValidationFailures(t *testing.T) {
	dir := t.TempDir()
	if err := os.WriteFile(filepath.Join(dir, "empty-header.csv"), []byte("username,\nalice,\n"), 0o644); err != nil {
		t.Fatal(err)
	}
	tests := []struct {
		name string
		data DataSet
		want string
	}{
		{name: "missing file", data: DataSet{}, want: "file is required"},
		{name: "bad sharing", data: DataSet{File: "missing.csv", Variables: []string{"x"}, Sharing: "everyone"}, want: "sharing"},
		{name: "missing csv", data: DataSet{File: "missing.csv"}, want: "read CSV"},
		{name: "empty header", data: DataSet{File: "empty-header.csv"}, want: "empty"},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.data.NormalizeAndValidate("users", dir)
			if err == nil || !strings.Contains(err.Error(), tt.want) {
				t.Fatalf("error = %v, want substring %q", err, tt.want)
			}
		})
	}
}

func TestWebSocketMultiMessageValidation(t *testing.T) {
	raw := Spec{
		Name:   "ws-multi",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			Path:     "/chat",
			WebSocket: WebSocket{
				Timeout: Duration{Seconds: 10, Set: true},
				Messages: []WSMessage{
					{Send: "hello", Expect: &WSExpect{Contains: "hello"}},
					{Send: "world", Delay: Duration{Seconds: 1, Set: true}},
				},
			},
		}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	msgs := raw.Requests[0].WebSocket.Messages
	if len(msgs) != 2 {
		t.Fatalf("expected 2 messages, got %d", len(msgs))
	}
	if msgs[0].Type != "text" {
		t.Fatalf("type = %q", msgs[0].Type)
	}
	if msgs[0].Expect.Timeout.Seconds != 10 {
		t.Fatalf("expect timeout was not inherited: %+v", msgs[0].Expect.Timeout)
	}
}

func TestWebSocketLegacyNormalizesToMessages(t *testing.T) {
	raw := Spec{
		Name:   "ws-legacy",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			Path:     "/echo",
			WebSocket: WebSocket{
				Message:        "ping",
				ExpectContains: "pong",
				Timeout:        Duration{Seconds: 5, Set: true},
			},
		}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	msgs := raw.Requests[0].WebSocket.Messages
	if len(msgs) != 1 {
		t.Fatalf("expected 1 message, got %d", len(msgs))
	}
	if msgs[0].Send != "ping" || msgs[0].Expect == nil || msgs[0].Expect.Contains != "pong" {
		t.Fatalf("legacy not normalized: %+v", msgs[0])
	}
}

func TestWebSocketRejectsMixedLegacyAndMessages(t *testing.T) {
	request := Request{
		Protocol: "websocket",
		WebSocket: WebSocket{
			Message:  "legacy",
			Messages: []WSMessage{{Send: "new"}},
		},
	}
	err := request.NormalizeAndValidate(0)
	if err == nil || !strings.Contains(err.Error(), "cannot mix legacy") {
		t.Fatalf("error = %v", err)
	}
}

func TestWebSocketBinaryMessageValidation(t *testing.T) {
	raw := Spec{
		Name:   "ws-binary",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			WebSocket: WebSocket{
				Messages: []WSMessage{{Send: "aGVsbG8=", Type: "binary"}},
			},
		}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}

	rawBad := Spec{
		Name:   "ws-binary-bad",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			WebSocket: WebSocket{
				Messages: []WSMessage{{Send: "not-valid-base64!!!", Type: "binary"}},
			},
		}},
	}
	err := rawBad.NormalizeAndValidate()
	if err == nil || !strings.Contains(err.Error(), "valid base64") {
		t.Fatalf("error = %v", err)
	}
}

func TestWebSocketSubprotocolAndHeaders(t *testing.T) {
	raw := Spec{
		Name:   "ws-sub",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			WebSocket: WebSocket{
				Subprotocol: "graphql-ws",
				Headers:     map[string]string{"Authorization": "Bearer token"},
				Messages:    []WSMessage{{Send: "init"}},
			},
		}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	if raw.Requests[0].WebSocket.Subprotocol != "graphql-ws" {
		t.Fatalf("subprotocol = %q", raw.Requests[0].WebSocket.Subprotocol)
	}
}

func TestWebSocketResolveVariablesInMessages(t *testing.T) {
	raw := Spec{
		Name:      "ws-vars",
		Target:    "wss://echo.example.com",
		Variables: map[string]string{"greeting": "hello"},
		Requests: []Request{{
			Protocol: "websocket",
			WebSocket: WebSocket{
				Messages: []WSMessage{{
					Send:   "{{greeting}}",
					Expect: &WSExpect{Contains: "{{greeting}}"},
				}},
			},
		}},
	}
	resolved, err := raw.Resolve(nil)
	if err != nil {
		t.Fatalf("Resolve() error = %v", err)
	}
	msgs := resolved.Requests[0].WebSocket.Messages
	if msgs[0].Send != "hello" || msgs[0].Expect.Contains != "hello" {
		t.Fatalf("variable not resolved: %+v", msgs[0])
	}
}

func TestWebSocketDelayValidation(t *testing.T) {
	raw := Spec{
		Name:   "ws-delay",
		Target: "wss://echo.example.com",
		Requests: []Request{{
			Protocol: "websocket",
			WebSocket: WebSocket{
				Messages: []WSMessage{{
					Send:  "delayed",
					Delay: Duration{Seconds: 2, Set: true},
				}},
			},
		}},
	}
	if err := raw.NormalizeAndValidate(); err != nil {
		t.Fatalf("NormalizeAndValidate() error = %v", err)
	}
	if raw.Requests[0].WebSocket.Messages[0].Delay.Seconds != 2 {
		t.Fatalf("delay = %+v", raw.Requests[0].WebSocket.Messages[0].Delay)
	}
}

func intPtr(value int) *int {
	return &value
}
