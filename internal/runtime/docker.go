package runtime

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
)

const DefaultJMeterImage = "justb4/jmeter:latest"

type RunOptions struct {
	Image      string
	WorkDir    string
	JMXPath    string
	ResultsDir string
	JTLName    string
}

func Doctor() []Check {
	return []Check{
		checkCommand("docker", "Docker CLI"),
		checkDocker(),
	}
}

type Check struct {
	Name    string
	Passed  bool
	Message string
}

func RunJMeter(options RunOptions) error {
	if options.Image == "" {
		options.Image = DefaultJMeterImage
	}
	if options.JTLName == "" {
		options.JTLName = "results.jtl"
	}
	absWorkDir, err := filepath.Abs(options.WorkDir)
	if err != nil {
		return err
	}
	jmxAbs, err := filepath.Abs(options.JMXPath)
	if err != nil {
		return err
	}
	resultsAbs, err := filepath.Abs(options.ResultsDir)
	if err != nil {
		return err
	}
	if err := os.MkdirAll(resultsAbs, 0o755); err != nil {
		return err
	}
	relJMX, err := filepath.Rel(absWorkDir, jmxAbs)
	if err != nil || relJMX == "." || relJMX == ".." || strings.HasPrefix(relJMX, ".."+string(filepath.Separator)) {
		return errors.New("JMX file must be inside the working directory")
	}

	args := []string{
		"run", "--rm",
		"-v", absWorkDir + ":/work",
		"-w", "/work",
		options.Image,
		"-n",
		"-t", filepath.ToSlash(relJMX),
		"-l", "/work/" + filepath.ToSlash(filepath.Join(mustRel(absWorkDir, resultsAbs), options.JTLName)),
	}
	cmd := exec.Command("docker", args...)
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	return cmd.Run()
}

func checkCommand(command string, name string) Check {
	if _, err := exec.LookPath(command); err != nil {
		return Check{Name: name, Passed: false, Message: fmt.Sprintf("%s not found in PATH", command)}
	}
	return Check{Name: name, Passed: true, Message: "found"}
}

func checkDocker() Check {
	cmd := exec.Command("docker", "version", "--format", "{{.Server.Version}}")
	output, err := cmd.Output()
	if err != nil {
		return Check{Name: "Docker daemon", Passed: false, Message: "docker daemon is not reachable"}
	}
	return Check{Name: "Docker daemon", Passed: true, Message: "server " + stringTrim(output)}
}

func mustRel(base, target string) string {
	rel, err := filepath.Rel(base, target)
	if err != nil {
		return target
	}
	return rel
}

func stringTrim(value []byte) string {
	result := string(value)
	for len(result) > 0 && (result[len(result)-1] == '\n' || result[len(result)-1] == '\r' || result[len(result)-1] == ' ') {
		result = result[:len(result)-1]
	}
	return result
}
