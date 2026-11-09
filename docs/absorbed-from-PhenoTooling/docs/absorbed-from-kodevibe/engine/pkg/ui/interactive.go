package ui

import (
	"bufio"
	"fmt"
	"os"
	"strconv"
	"strings"
	"time"
	"unicode"

	"kodevibe/internal/models"

	"github.com/fatih/color"
)

// InteractiveUI provides an enhanced CLI experience
type InteractiveUI struct {
	scanner *bufio.Scanner
	output  *color.Color
	success *color.Color
	warning *color.Color
	error   *color.Color
}

// NewInteractiveUI creates a new interactive UI instance
func NewInteractiveUI() *InteractiveUI {
	return &InteractiveUI{
		scanner: bufio.NewScanner(os.Stdin),
		output:  color.New(color.FgCyan),
		success: color.New(color.FgGreen),
		warning: color.New(color.FgYellow),
		error:   color.New(color.FgRed),
	}
}

// DisplayWelcome shows the KodeVibe welcome screen
func (ui *InteractiveUI) DisplayWelcome() {
	ui.ClearScreen()
	ui.PrintBanner()
	fmt.Println()
	ui.success.Println("🌊 Welcome to KodeVibe - Advanced Code Quality Analysis Tool")
	fmt.Println("   Enhance your code quality with AI-powered insights")
	fmt.Println()
}

// PrintBanner displays the KodeVibe ASCII banner
func (ui *InteractiveUI) PrintBanner() {
	banner := `
╔══════════════════════════════════════════════════════════════╗
║  ██╗  ██╗ ██████╗ ██████╗ ███████╗██╗   ██╗██╗██████╗ ███████╗ ║
║  ██║ ██╔╝██╔═══██╗██╔══██╗██╔════╝██║   ██║██║██╔══██╗██╔════╝ ║
║  █████╔╝ ██║   ██║██║  ██║█████╗  ██║   ██║██║██████╔╝█████╗   ║
║  ██╔═██╗ ██║   ██║██║  ██║██╔══╝  ╚██╗ ██╔╝██║██╔══██╗██╔══╝   ║
║  ██║  ██╗╚██████╔╝██████╔╝███████╗ ╚████╔╝ ██║██████╔╝███████╗ ║
║  ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚══════╝  ╚═══╝  ╚═╝╚═════╝ ╚══════╝ ║
╚══════════════════════════════════════════════════════════════╝`
	ui.output.Println(banner)
}

// ClearScreen clears the terminal screen
func (ui *InteractiveUI) ClearScreen() {
	fmt.Print("\033[2J\033[H")
}

// ShowMainMenu displays the main menu options
func (ui *InteractiveUI) ShowMainMenu() int {
	fmt.Println("\n📋 What would you like to do?")
	fmt.Println("   1. 🔍 Quick Analysis")
	fmt.Println("   2. 🔧 Interactive Configuration")
	fmt.Println("   3. 📊 View Previous Reports")
	fmt.Println("   4. 🛠️  Advanced Options")
	fmt.Println("   5. 🌐 Start Web Interface")
	fmt.Println("   6. 🔗 MCP Integration")
	fmt.Println("   7. ❓ Help & Documentation")
	fmt.Println("   8. 🚪 Exit")

	return ui.GetMenuChoice(1, 8)
}

// GetMenuChoice prompts for and validates menu selection
func (ui *InteractiveUI) GetMenuChoice(min, max int) int {
	for {
		ui.output.Print(fmt.Sprintf("\n   Please select an option (%d-%d): ", min, max))
		if ui.scanner.Scan() {
			input := strings.TrimSpace(ui.scanner.Text())
			if choice, err := strconv.Atoi(input); err == nil {
				if choice >= min && choice <= max {
					return choice
				}
			}
		}
		ui.error.Printf("   Invalid selection. Please enter a number between %d and %d.\n", min, max)
	}
}

// GetInput prompts for user input with a message
func (ui *InteractiveUI) GetInput(prompt string) string {
	ui.output.Print(prompt)
	if ui.scanner.Scan() {
		return strings.TrimSpace(ui.scanner.Text())
	}
	return ""
}

// GetYesNo prompts for yes/no confirmation
func (ui *InteractiveUI) GetYesNo(prompt string) bool {
	for {
		response := ui.GetInput(prompt + " (y/n): ")
		switch strings.ToLower(response) {
		case "y", "yes", "1", "true":
			return true
		case "n", "no", "0", "false":
			return false
		default:
			ui.error.Println("   Please enter 'y' for yes or 'n' for no.")
		}
	}
}

// ShowProgress displays a progress indicator
func (ui *InteractiveUI) ShowProgress(message string, duration time.Duration) {
	ui.output.Printf("🔄 %s", message)

	ticker := time.NewTicker(duration / 20)
	defer ticker.Stop()

	progress := []string{"⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"}
	i := 0

	for range ticker.C {
		fmt.Printf("\r🔄 %s %s", message, progress[i%len(progress)])
		i++
		if i >= 20 {
			break
		}
	}
	fmt.Printf("\r✅ %s Complete!\n", message)
}

// DisplayVibesSelection shows available vibes for selection
func (ui *InteractiveUI) DisplayVibesSelection() []string {
	vibes := []string{
		"security", "performance", "readability", "maintainability",
		"testing", "documentation", "complexity",
	}

	fmt.Println("\n🎯 Select Vibes to Analyze:")
	for i, vibe := range vibes {
		fmt.Printf("   %d. %s\n", i+1, toTitle(vibe))
	}
	fmt.Println("   8. All Vibes")
	fmt.Println("   9. Custom Selection")

	choice := ui.GetMenuChoice(1, 9)

	switch choice {
	case 8:
		return vibes
	case 9:
		return ui.GetCustomVibesSelection(vibes)
	default:
		return []string{vibes[choice-1]}
	}
}

// GetCustomVibesSelection allows multiple vibe selection
func (ui *InteractiveUI) GetCustomVibesSelection(available []string) []string {
	var selected []string

	fmt.Println("\n🎯 Select multiple vibes (comma-separated numbers):")
	for i, vibe := range available {
		fmt.Printf("   %d. %s\n", i+1, toTitle(vibe))
	}

	input := ui.GetInput("   Enter your selection: ")
	selections := strings.Split(input, ",")

	for _, sel := range selections {
		if idx, err := strconv.Atoi(strings.TrimSpace(sel)); err == nil {
			if idx >= 1 && idx <= len(available) {
				selected = append(selected, available[idx-1])
			}
		}
	}

	if len(selected) == 0 {
		ui.warning.Println("   No valid selections made. Using all vibes.")
		return available
	}

	ui.success.Printf("   Selected: %s\n", strings.Join(selected, ", "))
	return selected
}

// DisplayAnalysisResults shows the analysis results in a formatted way
func (ui *InteractiveUI) DisplayAnalysisResults(results *models.AnalysisResult) {
	ui.ClearScreen()
	ui.success.Println("📊 Analysis Results")
	fmt.Println("═══════════════════")

	// Overall Score
	ui.DisplayOverallScore(results.OverallScore)

	// Individual Vibe Results
	fmt.Println("\n📋 Detailed Results:")
	for _, result := range results.VibeResults {
		ui.DisplayVibeResult(result)
	}

	// Issues Summary
	if len(results.Issues) > 0 {
		ui.DisplayIssuesSummary(results.Issues)
	}

	// Recommendations
	if len(results.Recommendations) > 0 {
		ui.DisplayRecommendations(results.Recommendations)
	}
}

// DisplayOverallScore shows the overall analysis score
func (ui *InteractiveUI) DisplayOverallScore(score float64) {
	fmt.Printf("\n🎯 Overall Score: ")

	switch {
	case score >= 90:
		ui.success.Printf("%.1f/100 ⭐⭐⭐⭐⭐ Excellent!\n", score)
	case score >= 80:
		ui.success.Printf("%.1f/100 ⭐⭐⭐⭐ Very Good\n", score)
	case score >= 70:
		ui.warning.Printf("%.1f/100 ⭐⭐⭐ Good\n", score)
	case score >= 60:
		ui.warning.Printf("%.1f/100 ⭐⭐ Fair\n", score)
	default:
		ui.error.Printf("%.1f/100 ⭐ Needs Improvement\n", score)
	}
}

// DisplayVibeResult shows individual vibe analysis results
func (ui *InteractiveUI) DisplayVibeResult(result models.VibeResult) {
	fmt.Printf("\n   🔹 %s: ", toTitle(result.Name))

	switch {
	case result.Score >= 90:
		ui.success.Printf("%.1f/100 ✅\n", result.Score)
	case result.Score >= 70:
		ui.warning.Printf("%.1f/100 ⚠️\n", result.Score)
	default:
		ui.error.Printf("%.1f/100 ❌\n", result.Score)
	}

	if result.Details != "" {
		fmt.Printf("      %s\n", result.Details)
	}
}

// DisplayIssuesSummary shows found issues
func (ui *InteractiveUI) DisplayIssuesSummary(issues []models.Issue) {
	fmt.Println("\n🚨 Issues Found:")

	severityCount := make(map[string]int)
	for _, issue := range issues {
		severityCount[string(issue.Severity)]++

		var severityColor *color.Color
		switch issue.Severity {
		case models.SeverityCritical, models.SeverityError:
			severityColor = ui.error
		case models.SeverityWarning:
			severityColor = ui.warning
		default:
			severityColor = ui.output
		}

		severityColor.Printf("   [%s] %s:%d - %s\n",
			strings.ToUpper(string(issue.Severity)),
			issue.File,
			issue.Line,
			issue.Message)
	}

	fmt.Printf("\n📈 Summary: ")
	if count := severityCount[string(models.SeverityCritical)]; count > 0 {
		ui.error.Printf("%d Critical ", count)
	}
	if count := severityCount[string(models.SeverityError)]; count > 0 {
		ui.error.Printf("%d Error ", count)
	}
	if count := severityCount[string(models.SeverityWarning)]; count > 0 {
		ui.warning.Printf("%d Warning ", count)
	}
	if count := severityCount[string(models.SeverityInfo)]; count > 0 {
		ui.output.Printf("%d Info ", count)
	}
	fmt.Println("issues found")
}

// DisplayRecommendations shows improvement recommendations
func (ui *InteractiveUI) DisplayRecommendations(recommendations []string) {
	fmt.Println("\n💡 Recommendations:")
	for i, rec := range recommendations {
		ui.output.Printf("   %d. %s\n", i+1, rec)
	}
}

// ShowAdvancedOptions displays advanced configuration options
func (ui *InteractiveUI) ShowAdvancedOptions() {
	fmt.Println("\n🛠️  Advanced Options:")
	fmt.Println("   1. 🔧 Configure Thresholds")
	fmt.Println("   2. 📁 Set Custom Output Directory")
	fmt.Println("   3. 🔍 Custom File Patterns")
	fmt.Println("   4. 🚀 Performance Settings")
	fmt.Println("   5. 🔒 Security Configuration")
	fmt.Println("   6. 🔙 Back to Main Menu")
}

// ShowHelp displays help information
func (ui *InteractiveUI) ShowHelp() {
	fmt.Println("\n❓ KodeVibe Help & Documentation")
	fmt.Println("═══════════════════════════════")
	fmt.Println("\n🎯 Available Analysis Types (Vibes):")
	fmt.Println("   • Security: Scans for security vulnerabilities and best practices")
	fmt.Println("   • Performance: Analyzes code efficiency and optimization opportunities")
	fmt.Println("   • Readability: Evaluates code clarity and documentation")
	fmt.Println("   • Maintainability: Assesses code structure and design patterns")
	fmt.Println("   • Testing: Reviews test coverage and quality")
	fmt.Println("   • Documentation: Checks documentation completeness")
	fmt.Println("   • Complexity: Measures code complexity metrics")

	fmt.Println("\n🚀 Quick Start:")
	fmt.Println("   1. Select 'Quick Analysis' from the main menu")
	fmt.Println("   2. Choose your target directory")
	fmt.Println("   3. Select which vibes to run")
	fmt.Println("   4. Review the generated report")

	fmt.Println("\n🌐 Web Interface:")
	fmt.Println("   • Access real-time dashboards")
	fmt.Println("   • Interactive report viewing")
	fmt.Println("   • Export capabilities")

	fmt.Println("\n🔗 MCP Integration:")
	fmt.Println("   • Connect with AI development workflows")
	fmt.Println("   • Enhanced context sharing")
	fmt.Println("   • Automated improvements")
}

// WaitForKeyPress waits for user to press enter
func (ui *InteractiveUI) WaitForKeyPress() {
	ui.output.Print("\nPress Enter to continue...")
	ui.scanner.Scan()
}

// DisplayError shows an error message
func (ui *InteractiveUI) DisplayError(message string) {
	ui.error.Printf("❌ Error: %s\n", message)
}

// DisplaySuccess shows a success message
func (ui *InteractiveUI) DisplaySuccess(message string) {
	ui.success.Printf("✅ %s\n", message)
}

// DisplayWarning shows a warning message
func (ui *InteractiveUI) DisplayWarning(message string) {
	ui.warning.Printf("⚠️  %s\n", message)
}

// toTitle converts string to title case without deprecated strings.Title
func toTitle(s string) string {
	if len(s) == 0 {
		return s
	}
	r := []rune(s)
	r[0] = unicode.ToUpper(r[0])
	return string(r)
}
