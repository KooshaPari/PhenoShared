package main

import (
	"os"

	"github.com/phenotype/phenoShared/cmd/promptscrape/cmd"
)

func main() {
	if err := cmd.Execute(); err != nil {
		os.Exit(1)
	}
}
