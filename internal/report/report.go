package report

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"html"
	"math"
	"os"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"github.com/devaryakjha/loadwright/internal/spec"
)

type Summary struct {
	TotalSamples int                 `json:"total_samples"`
	Successful   int                 `json:"successful"`
	Failed       int                 `json:"failed"`
	ErrorRate    float64             `json:"error_rate"`
	AverageMS    float64             `json:"average_ms"`
	MinMS        float64             `json:"min_ms"`
	MaxMS        float64             `json:"max_ms"`
	P50MS        float64             `json:"p50_ms"`
	P90MS        float64             `json:"p90_ms"`
	P95MS        float64             `json:"p95_ms"`
	P99MS        float64             `json:"p99_ms"`
	Endpoints    map[string]Endpoint `json:"endpoints"`
	Thresholds   []ThresholdResult   `json:"thresholds"`
}

type Endpoint struct {
	Count     int     `json:"count"`
	Failed    int     `json:"failed"`
	AverageMS float64 `json:"average_ms"`
	P95MS     float64 `json:"p95_ms"`
}

type ThresholdResult struct {
	Name   string  `json:"name"`
	Limit  float64 `json:"limit"`
	Actual float64 `json:"actual"`
	Passed bool    `json:"passed"`
}

func ParseJTL(path string, thresholds spec.Thresholds) (*Summary, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, err
	}
	defer file.Close()

	reader := csv.NewReader(file)
	reader.FieldsPerRecord = -1
	rows, err := reader.ReadAll()
	if err != nil {
		return nil, err
	}
	if len(rows) == 0 {
		return &Summary{Endpoints: map[string]Endpoint{}}, nil
	}

	header := map[string]int{}
	for i, name := range rows[0] {
		header[name] = i
	}

	var elapsedValues []float64
	totalElapsed := 0.0
	minElapsed := math.Inf(1)
	maxElapsed := 0.0
	endpointValues := map[string][]float64{}
	endpointFailed := map[string]int{}
	summary := &Summary{Endpoints: map[string]Endpoint{}}

	for _, row := range rows[1:] {
		elapsed := fieldFloat(row, header, "elapsed")
		label := field(row, header, "label")
		if label == "" {
			label = "unknown"
		}
		success := strings.EqualFold(field(row, header, "success"), "true")
		summary.TotalSamples++
		if success {
			summary.Successful++
		} else {
			summary.Failed++
			endpointFailed[label]++
		}
		elapsedValues = append(elapsedValues, elapsed)
		endpointValues[label] = append(endpointValues[label], elapsed)
		totalElapsed += elapsed
		if elapsed < minElapsed {
			minElapsed = elapsed
		}
		if elapsed > maxElapsed {
			maxElapsed = elapsed
		}
	}

	if summary.TotalSamples == 0 {
		return summary, nil
	}
	sort.Float64s(elapsedValues)
	summary.ErrorRate = float64(summary.Failed) / float64(summary.TotalSamples) * 100
	summary.AverageMS = totalElapsed / float64(summary.TotalSamples)
	summary.MinMS = minElapsed
	summary.MaxMS = maxElapsed
	summary.P50MS = percentile(elapsedValues, 50)
	summary.P90MS = percentile(elapsedValues, 90)
	summary.P95MS = percentile(elapsedValues, 95)
	summary.P99MS = percentile(elapsedValues, 99)

	for label, values := range endpointValues {
		sort.Float64s(values)
		total := 0.0
		for _, value := range values {
			total += value
		}
		summary.Endpoints[label] = Endpoint{
			Count:     len(values),
			Failed:    endpointFailed[label],
			AverageMS: total / float64(len(values)),
			P95MS:     percentile(values, 95),
		}
	}

	summary.Thresholds = EvaluateThresholds(summary, thresholds)
	return summary, nil
}

func EvaluateThresholds(summary *Summary, thresholds spec.Thresholds) []ThresholdResult {
	var results []ThresholdResult
	if thresholds.ErrorRateLT != nil {
		results = append(results, ThresholdResult{
			Name: "error_rate_lt", Limit: *thresholds.ErrorRateLT, Actual: summary.ErrorRate,
			Passed: summary.ErrorRate < *thresholds.ErrorRateLT,
		})
	}
	if thresholds.P95MsLT != nil {
		results = append(results, ThresholdResult{
			Name: "p95_ms_lt", Limit: *thresholds.P95MsLT, Actual: summary.P95MS,
			Passed: summary.P95MS < *thresholds.P95MsLT,
		})
	}
	if thresholds.AvgMsLT != nil {
		results = append(results, ThresholdResult{
			Name: "avg_ms_lt", Limit: *thresholds.AvgMsLT, Actual: summary.AverageMS,
			Passed: summary.AverageMS < *thresholds.AvgMsLT,
		})
	}
	return results
}

func (s *Summary) Passed() bool {
	for _, threshold := range s.Thresholds {
		if !threshold.Passed {
			return false
		}
	}
	return true
}

func WriteAll(summary *Summary, outDir string) error {
	if err := os.MkdirAll(outDir, 0o755); err != nil {
		return err
	}
	data, err := json.MarshalIndent(summary, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(outDir, "summary.json"), append(data, '\n'), 0o644); err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(outDir, "summary.md"), []byte(RenderMarkdown(summary)), 0o644); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(outDir, "index.html"), []byte(RenderHTML(summary)), 0o644)
}

func RenderMarkdown(s *Summary) string {
	var b strings.Builder
	b.WriteString("# JMeter Test Summary\n\n")
	fmt.Fprintf(&b, "- Total samples: %d\n", s.TotalSamples)
	fmt.Fprintf(&b, "- Successful: %d\n", s.Successful)
	fmt.Fprintf(&b, "- Failed: %d\n", s.Failed)
	fmt.Fprintf(&b, "- Error rate: %.2f%%\n", s.ErrorRate)
	fmt.Fprintf(&b, "- Average: %.2f ms\n", s.AverageMS)
	fmt.Fprintf(&b, "- p95: %.2f ms\n", s.P95MS)
	fmt.Fprintf(&b, "- p99: %.2f ms\n", s.P99MS)
	if len(s.Thresholds) > 0 {
		b.WriteString("\n## Thresholds\n\n")
		for _, threshold := range s.Thresholds {
			status := "PASS"
			if !threshold.Passed {
				status = "FAIL"
			}
			fmt.Fprintf(&b, "- %s: %s actual %.2f limit %.2f\n", threshold.Name, status, threshold.Actual, threshold.Limit)
		}
	}
	return b.String()
}

func RenderHTML(s *Summary) string {
	status := "PASS"
	if !s.Passed() {
		status = "FAIL"
	}
	return fmt.Sprintf(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Loadwright report</title>
  <style>
    body { font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 32px; color: #17202a; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
    .metric { border: 1px solid #d8dee4; border-radius: 8px; padding: 16px; }
    .metric strong { display: block; font-size: 28px; margin-bottom: 4px; }
    .pass { color: #166534; }
    .fail { color: #991b1b; }
    table { width: 100%%; border-collapse: collapse; margin-top: 24px; }
    th, td { border-bottom: 1px solid #d8dee4; padding: 8px; text-align: left; }
  </style>
</head>
<body>
  <h1>Loadwright report <span class="%s">%s</span></h1>
  <div class="grid">
    <div class="metric"><strong>%d</strong>Total samples</div>
    <div class="metric"><strong>%d</strong>Failed</div>
    <div class="metric"><strong>%.2f%%</strong>Error rate</div>
    <div class="metric"><strong>%.2f ms</strong>Average</div>
    <div class="metric"><strong>%.2f ms</strong>p95</div>
    <div class="metric"><strong>%.2f ms</strong>p99</div>
  </div>
  %s
</body>
</html>
`, strings.ToLower(status), status, s.TotalSamples, s.Failed, s.ErrorRate, s.AverageMS, s.P95MS, s.P99MS, renderThresholdTable(s))
}

func renderThresholdTable(s *Summary) string {
	if len(s.Thresholds) == 0 {
		return ""
	}
	var b strings.Builder
	b.WriteString("<h2>Thresholds</h2><table><thead><tr><th>Name</th><th>Actual</th><th>Limit</th><th>Status</th></tr></thead><tbody>")
	for _, threshold := range s.Thresholds {
		status := "PASS"
		className := "pass"
		if !threshold.Passed {
			status = "FAIL"
			className = "fail"
		}
		fmt.Fprintf(&b, "<tr><td>%s</td><td>%.2f</td><td>%.2f</td><td class=\"%s\">%s</td></tr>", html.EscapeString(threshold.Name), threshold.Actual, threshold.Limit, className, status)
	}
	b.WriteString("</tbody></table>")
	return b.String()
}

func percentile(sorted []float64, pct float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	if len(sorted) == 1 {
		return sorted[0]
	}
	rank := (pct / 100) * float64(len(sorted)-1)
	lower := int(math.Floor(rank))
	upper := int(math.Ceil(rank))
	if lower == upper {
		return sorted[lower]
	}
	weight := rank - float64(lower)
	return sorted[lower]*(1-weight) + sorted[upper]*weight
}

func field(row []string, header map[string]int, name string) string {
	index, ok := header[name]
	if !ok || index >= len(row) {
		return ""
	}
	return row[index]
}

func fieldFloat(row []string, header map[string]int, name string) float64 {
	parsed, _ := strconv.ParseFloat(field(row, header, name), 64)
	return parsed
}
