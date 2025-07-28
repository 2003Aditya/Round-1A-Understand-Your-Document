package processor

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"sync"
	"time"

	"github.com/2003Aditya/internal/utils"
)

var (
	inputDir     = resolvePath("/app/input", "../input")
	tempDir      = resolvePath("/app/temp_output", "../temp_output")
	outputDir    = resolvePath("/app/output", "../output")
	pythonScript = resolvePath("/extractor/extract.py", "../extractor/extract.py")
	chunks       = 5
)

type Heading struct {
	Level string `json:"level"`
	Text  string `json:"text"`
	Page  int    `json:"page"`
}

type FinalOutput struct {
	Title   string    `json:"title"`
	Outline []Heading `json:"outline"`
}

// resolvePath tries dockerPath first, falls back to localPath
func resolvePath(dockerPath, localPath string) string {
	if _, err := os.Stat(dockerPath); err == nil {
		return dockerPath
	}
	return localPath
}

func ProcessPDF(filename string) {
	pdfPath := filepath.Join(inputDir, filename)

	// Count total pages using Python script
	cmd := exec.Command("python3", pythonScript, "--count", pdfPath)
    fmt.Printf("🧪 Running: python3 %s --count %s\n", pythonScript, pdfPath)
	output, err := cmd.Output()
	if err != nil {
		log.Fatalf("❌ Failed to count pages in %s: %v", filename, err)
	}
	totalPages, _ := strconv.Atoi(strings.TrimSpace(string(output)))
	fmt.Printf("📄 Total pages in %s: %d\n", filename, totalPages)

	// Divide into chunks
	chunkSize := (totalPages + chunks - 1) / chunks
	var wg sync.WaitGroup
	jsonFiles := []string{}

	for i := 0; i < chunks; i++ {
		start := i * chunkSize
		end := utils.Min((i+1)*chunkSize, totalPages)
		if start >= end {
			fmt.Printf("⚠️ Skipping empty chunk: %d-%d\n", start, end)
			continue
		}

		wg.Add(1)
		outputJSON := fmt.Sprintf("%s_%d_%d.json", strings.TrimSuffix(filename, ".pdf"), start, end)
		outputPath := filepath.Join(tempDir, outputJSON)
		jsonFiles = append(jsonFiles, outputPath)

		go func(start, end int, outPath string, chunkNum int) {
			defer wg.Done()
			fmt.Printf("🚀 Goroutine %d: Processing pages %d–%d → %s\n", chunkNum, start, end, outPath)
			startTime := time.Now()

			cmd := exec.Command("python3", pythonScript, pdfPath, fmt.Sprint(start), fmt.Sprint(end), outPath)
			cmd.Stdout = os.Stdout
			cmd.Stderr = os.Stderr

			if err := cmd.Run(); err != nil {
				log.Printf("❌ Error processing chunk %d (%d–%d): %v", chunkNum, start, end, err)
			} else {
				fmt.Printf("✅ Goroutine %d: Finished %d–%d in %v\n", chunkNum, start, end, time.Since(startTime))
			}
		}(start, end, outputPath, i+1)
	}

	wg.Wait()

	// Merge JSON chunks into final output
	merged := MergeHeadings(jsonFiles)
	// final := FinalOutput{
	// 	Title:   strings.TrimSuffix(filename, ".pdf"),
	// 	Outline: merged,
	// }
    finalTitle := GlobalTitle
    if finalTitle == "" {
        finalTitle = strings.TrimSuffix(filename, ".pdf")
    }

    final := FinalOutput{
        Title:   finalTitle,
        Outline: merged,
    }


	finalPath := filepath.Join(outputDir, strings.TrimSuffix(filename, ".pdf")+".json")
	file, _ := os.Create(finalPath)
	defer file.Close()

	enc := json.NewEncoder(file)
	enc.SetIndent("", "  ")
	enc.Encode(final)
	fmt.Printf("📦 Merged final output: %s\n", finalPath)
}

