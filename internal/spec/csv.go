package spec

import (
	"encoding/csv"
	"fmt"
	"os"
	"strings"
)

func ReadCSVHeader(path string) ([]string, error) {
	file, err := os.Open(path)
	if err != nil {
		return nil, fmt.Errorf("read CSV: %w", err)
	}
	defer file.Close()

	reader := csv.NewReader(file)
	header, err := reader.Read()
	if err != nil {
		return nil, fmt.Errorf("read CSV header: %w", err)
	}
	for index, value := range header {
		header[index] = strings.TrimSpace(value)
		if header[index] == "" {
			return nil, fmt.Errorf("CSV header column %d is empty", index+1)
		}
	}
	return header, nil
}
