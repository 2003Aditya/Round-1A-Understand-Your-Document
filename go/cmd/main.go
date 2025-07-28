package main

import (
	"fmt"
	"log"
	"os"
	"strings"
	"time"

	"github.com/2003Aditya/internal/processor"
)

// resolvePath tries dockerPath first, falls back to localPath
func resolvePath(dockerPath, localPath string) string {
	if _, err := os.Stat(dockerPath); err == nil {
		return dockerPath
	}
	fmt.Printf("📂 Falling back to local path: %s\n", localPath)
	return localPath
}

func main() {
	start := time.Now()

	inputDir := resolvePath("/app/input", "../input")

	files, err := os.ReadDir(inputDir)
	if err != nil {
		log.Fatalf("❌ Failed to read input dir: %v", err)
	}

	for _, file := range files {
		if strings.HasSuffix(file.Name(), ".pdf") {
			fmt.Printf("📄 Processing: %s\n", file.Name())
			processStart := time.Now()

			// Process PDF
			processor.ProcessPDF(file.Name())

			fmt.Printf("⏱️ Finished %s in %v\n\n", file.Name(), time.Since(processStart))
		}
	}

	fmt.Printf("✅ All PDFs processed in %v.\n", time.Since(start))
}

