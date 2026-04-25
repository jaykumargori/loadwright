package runtime

import (
	"errors"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	goruntime "runtime"
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

type DoctorOptions struct {
	Image   string
	Deep    bool
	WorkDir string
}

func Doctor(options DoctorOptions) []Check {
	if options.Image == "" {
		options.Image = DefaultJMeterImage
	}
	if options.WorkDir == "" {
		options.WorkDir = "."
	}
	checks := []Check{
		checkCommand("docker", "Docker CLI"),
		checkDocker(),
		checkWritableDir(filepath.Join(options.WorkDir, "tests"), "tests directory"),
		checkWritableDir(filepath.Join(options.WorkDir, "results"), "results directory"),
		checkImage(options.Image),
	}
	if options.Deep {
		checks = append(checks, checkJMeterRuntime(options.Image))
	}
	return checks
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

func checkWritableDir(path string, name string) Check {
	if err := os.MkdirAll(path, 0o755); err != nil {
		return Check{Name: name, Passed: false, Message: err.Error()}
	}
	probe, err := os.CreateTemp(path, ".loadwright-doctor-*")
	if err != nil {
		return Check{Name: name, Passed: false, Message: "not writable: " + err.Error()}
	}
	probePath := probe.Name()
	_ = probe.Close()
	_ = os.Remove(probePath)
	return Check{Name: name, Passed: true, Message: "writable"}
}

func checkImage(image string) Check {
	cmd := exec.Command("docker", "image", "inspect", image, "--format", "{{.Architecture}}")
	output, err := cmd.Output()
	if err != nil {
		return Check{Name: "JMeter image", Passed: true, Message: image + " not local; Docker will pull it on first run"}
	}
	arch := stringTrim(output)
	message := image + " available"
	if arch != "" && arch != goruntime.GOARCH {
		message += fmt.Sprintf(" (%s image on %s host; Docker may use emulation)", arch, goruntime.GOARCH)
	}
	return Check{Name: "JMeter image", Passed: true, Message: message}
}

func checkJMeterRuntime(image string) Check {
	cmd := exec.Command("docker", "run", "--rm", image, "--version")
	output, err := cmd.CombinedOutput()
	if err != nil {
		return Check{Name: "JMeter runtime", Passed: false, Message: err.Error()}
	}
	version := firstVersionLine(string(output))
	if version == "" {
		version = "started successfully"
	}
	return Check{Name: "JMeter runtime", Passed: true, Message: version}
}

func firstVersionLine(output string) string {
	versionPattern := regexp.MustCompile(`\b([0-9]+\.[0-9]+(?:\.[0-9]+)?)\b`)
	for _, line := range strings.Split(output, "\n") {
		trimmed := strings.TrimSpace(line)
		if strings.Contains(trimmed, "Apache JMeter") || strings.HasPrefix(trimmed, "Version ") {
			return trimmed
		}
		if strings.Contains(trimmed, "____") {
			matches := versionPattern.FindStringSubmatch(trimmed)
			if len(matches) > 1 {
				return "Apache JMeter " + matches[1]
			}
		}
	}
	return ""
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
