package spec

import (
	"os"
	"path/filepath"

	"gopkg.in/yaml.v3"
)

func WriteFile(s *Spec, path string) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	data, err := yaml.Marshal(s)
	if err != nil {
		return err
	}
	return os.WriteFile(path, data, 0o644)
}
