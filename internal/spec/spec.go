package spec

import (
	"errors"
	"fmt"
	"net/url"
	"os"
	"strconv"
	"strings"

	"gopkg.in/yaml.v3"
)

type Duration struct {
	Seconds int
	Set     bool
}

func (d *Duration) UnmarshalYAML(value *yaml.Node) error {
	var raw any
	if err := value.Decode(&raw); err != nil {
		return err
	}
	seconds, err := ParseDuration(raw)
	if err != nil {
		return err
	}
	d.Seconds = seconds
	d.Set = true
	return nil
}

func ParseDuration(raw any) (int, error) {
	switch value := raw.(type) {
	case int:
		if value <= 0 {
			return 0, errors.New("duration must be greater than 0")
		}
		return value, nil
	case string:
		trimmed := strings.TrimSpace(strings.ToLower(value))
		if trimmed == "" {
			return 0, errors.New("duration cannot be empty")
		}
		multiplier := 1
		number := trimmed
		switch trimmed[len(trimmed)-1] {
		case 's':
			number = trimmed[:len(trimmed)-1]
		case 'm':
			number = trimmed[:len(trimmed)-1]
			multiplier = 60
		case 'h':
			number = trimmed[:len(trimmed)-1]
			multiplier = 3600
		}
		parsed, err := strconv.Atoi(number)
		if err != nil || parsed <= 0 {
			return 0, fmt.Errorf("duration must look like 30s, 5m, 1h, or an integer second value")
		}
		return parsed * multiplier, nil
	default:
		return 0, fmt.Errorf("duration must be a string or integer")
	}
}

type Spec struct {
	Name       string     `yaml:"name"`
	Target     string     `yaml:"target"`
	Load       Load       `yaml:"load"`
	Requests   []Request  `yaml:"requests"`
	Thresholds Thresholds `yaml:"thresholds"`
}

type Load struct {
	Users    int      `yaml:"users"`
	RampUp   Duration `yaml:"ramp_up"`
	Duration Duration `yaml:"duration"`
	Loops    *int     `yaml:"loops"`
}

type Request struct {
	Name    string            `yaml:"name"`
	Method  string            `yaml:"method"`
	Path    string            `yaml:"path"`
	Headers map[string]string `yaml:"headers"`
	Query   map[string]string `yaml:"query"`
	Body    any               `yaml:"body"`
	Expect  Expect            `yaml:"expect"`
}

type Expect struct {
	Status int `yaml:"status"`
}

type Thresholds struct {
	ErrorRateLT *float64 `yaml:"error_rate_lt"`
	P95MsLT     *float64 `yaml:"p95_ms_lt"`
	AvgMsLT     *float64 `yaml:"avg_ms_lt"`
}

func LoadFile(path string) (*Spec, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("read spec: %w", err)
	}
	var parsed Spec
	if err := yaml.Unmarshal(data, &parsed); err != nil {
		return nil, fmt.Errorf("parse YAML: %w", err)
	}
	if err := parsed.NormalizeAndValidate(); err != nil {
		return nil, err
	}
	return &parsed, nil
}

func (s *Spec) NormalizeAndValidate() error {
	s.Name = strings.TrimSpace(s.Name)
	if s.Name == "" {
		return errors.New("name is required")
	}
	s.Target = strings.TrimRight(strings.TrimSpace(s.Target), "/")
	parsedTarget, err := url.Parse(s.Target)
	if err != nil || parsedTarget.Scheme == "" || parsedTarget.Host == "" {
		return errors.New("target must be an absolute http or https URL")
	}
	if parsedTarget.Scheme != "http" && parsedTarget.Scheme != "https" {
		return errors.New("target must use http or https")
	}
	if s.Load.Users == 0 {
		s.Load.Users = 1
	}
	if s.Load.Users < 0 {
		return errors.New("load.users must be greater than 0")
	}
	if !s.Load.RampUp.Set {
		s.Load.RampUp = Duration{Seconds: 1, Set: true}
	}
	if s.Load.Loops == nil && !s.Load.Duration.Set {
		defaultLoops := 1
		s.Load.Loops = &defaultLoops
	}
	if s.Load.Loops != nil && *s.Load.Loops <= 0 {
		return errors.New("load.loops must be greater than 0")
	}
	if len(s.Requests) == 0 {
		return errors.New("requests must contain at least one request")
	}
	for index := range s.Requests {
		if err := s.Requests[index].NormalizeAndValidate(index); err != nil {
			return err
		}
	}
	return nil
}

func (r *Request) NormalizeAndValidate(index int) error {
	r.Method = strings.ToUpper(strings.TrimSpace(r.Method))
	if r.Method == "" {
		r.Method = "GET"
	}
	switch r.Method {
	case "GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS":
	default:
		return fmt.Errorf("requests[%d].method is not supported: %s", index, r.Method)
	}
	r.Path = strings.TrimSpace(r.Path)
	if !strings.HasPrefix(r.Path, "/") {
		return fmt.Errorf("requests[%d].path must start with /", index)
	}
	if strings.TrimSpace(r.Name) == "" {
		r.Name = r.Method + " " + r.Path
	}
	if r.Headers == nil {
		r.Headers = map[string]string{}
	}
	if r.Query == nil {
		r.Query = map[string]string{}
	}
	return nil
}
