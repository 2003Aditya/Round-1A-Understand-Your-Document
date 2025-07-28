package processor

import (
	"encoding/json"
	"log"
	"os"
	"sort"
)

// GlobalTitle is used to store the title from the first chunk
var GlobalTitle string

func MergeHeadings(files []string) []Heading {
	all := []Heading{}
	titleExtracted := false

	for _, f := range files {
		data, err := os.ReadFile(f)
		if err != nil {
			log.Printf("⚠️ Skipping %s: %v", f, err)
			continue
		}
		var part struct {
			Title   string    `json:"title"`
			Outline []Heading `json:"outline"`
		}
		if err := json.Unmarshal(data, &part); err != nil {
			log.Printf("⚠️ Invalid JSON in %s: %v", f, err)
			continue
		}

		if !titleExtracted && part.Title != "" {
			GlobalTitle = part.Title
			titleExtracted = true
		}

		all = append(all, part.Outline...)
	}

	sort.Slice(all, func(i, j int) bool {
		return all[i].Page < all[j].Page
	})

	return all
}

