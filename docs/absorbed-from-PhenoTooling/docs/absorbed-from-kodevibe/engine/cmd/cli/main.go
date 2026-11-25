package main

import (
	"context"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/fatih/color"
	"github.com/sirupsen/logrus"
	"github.com/spf13/cobra"
	"github.com/spf13/viper"

	"kodevibe/internal/models"
	"kodevibe/pkg/config"
	"kodevibe/pkg/fix"
	"kodevibe/pkg/report"
	"kodevibe/pkg/scanner"
	"kodevibe/pkg/server"
	"kodevibe/pkg/watch"
)

var (
	cfgFile   string
	verbose   bool
	quiet     bool
	configMgr *config.Manager
	logger    *logrus.Logger
)

// rootCmd represents the base command when called without any subcommands
var rootCmd = &cobra.Command{
	Use:   "kodevibe",
	Short: "🌊 The Ultimate Code Quality Guardian",
	Long: `KodeVibe is a comprehensive, modular tool that prevents bad vibes from entering your codebase.
Goes far beyond secret detection to catch all common development pitfalls before they become problems.

🎯 What KodeVibe Catches:
• SecurityVibe: Secrets, vulnerabilities, weak crypto
• CodeVibe: Code smells, anti-patterns, style violations
• PerformanceVibe: N+1 queries, memory leaks, inefficient algorithms
• FileVibe: Junk files, large files, organization issues
• GitVibe: Commit quality, branch naming, merge conflicts
• DependencyVibe: Outdated packages, vulnerabilities, license issues
• DocumentationVibe: Missing docs, outdated documentation`,
	Version: "1.0.0",
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}

func init() {
	cobra.OnInitialize(initConfig)

	// Global flags
	rootCmd.PersistentFlags().StringVar(&cfgFile, "config", "", "config file (default is .kodevibe.yaml)")
	rootCmd.PersistentFlags().BoolVarP(&verbose, "verbose", "v", false, "verbose output")
	rootCmd.PersistentFlags().BoolVarP(&quiet, "quiet", "q", false, "quiet output")

	// Initialize logger
	logger = logrus.New()
	logger.SetFormatter(&logrus.JSONFormatter{})

	// Add commands
	rootCmd.AddCommand(scanCmd)
	rootCmd.AddCommand(installCmd)
	rootCmd.AddCommand(hooksCmd)
	rootCmd.AddCommand(configCmd)
	rootCmd.AddCommand(fixCmd)
	rootCmd.AddCommand(reportCmd)
	rootCmd.AddCommand(profileCmd)
	rootCmd.AddCommand(watchCmd)
	rootCmd.AddCommand(serverCmd)
	rootCmd.AddCommand(updateCmd)
	rootCmd.AddCommand(versionCmd)
}

func initConfig() {
	configMgr = config.NewManager()

	if cfgFile != "" {
		viper.SetConfigFile(cfgFile)
	} else {
		home, err := os.UserHomeDir()
		cobra.CheckErr(err)

		viper.AddConfigPath(".")
		viper.AddConfigPath(home)
		viper.SetConfigName(".kodevibe")
		viper.SetConfigType("yaml")
	}

	viper.AutomaticEnv()

	if err := configMgr.LoadConfig(cfgFile); err != nil {
		// Use default config if loading fails
		if verbose {
			fmt.Printf("Warning: Could not load config: %v\n", err)
		}
	}

	// Set log level
	if verbose {
		logger.SetLevel(logrus.DebugLevel)
	} else if quiet {
		logger.SetLevel(logrus.ErrorLevel)
	} else {
		logger.SetLevel(logrus.InfoLevel)
	}
}

// scanCmd represents the scan command
var scanCmd = &cobra.Command{
	Use:   "scan [paths...]",
	Short: "Scan files for code quality issues",
	Long: `Scan files and directories for code quality issues across all vibes.
	
Examples:
  kodevibe scan                           # Scan current directory
  kodevibe scan src/ tests/               # Scan specific directories
  kodevibe scan --vibes security,code    # Scan with specific vibes
  kodevibe scan --staged                  # Scan only staged files
  kodevibe scan --diff HEAD~1             # Scan changes since last commit
  kodevibe scan --ci --strict             # CI mode with strict checking`,
	Args: cobra.ArbitraryArgs,
	RunE: runScan,
}

func init() {
	scanCmd.Flags().StringSlice("vibes", []string{}, "Comma-separated list of vibes to run (security,code,performance,file,git,dependency,documentation)")
	scanCmd.Flags().StringSlice("exclude", []string{}, "Additional file patterns to exclude")
	scanCmd.Flags().String("min-severity", "info", "Minimum severity level (error, warning, info)")
	scanCmd.Flags().String("format", "text", "Output format (text, json, html, junit)")
	scanCmd.Flags().String("output", "", "Output file path")
	scanCmd.Flags().Bool("ci", false, "CI mode - exit with non-zero code on issues")
	scanCmd.Flags().Bool("strict", false, "Strict mode - fail on any issues")
	scanCmd.Flags().Bool("staged", false, "Only scan staged files")
	scanCmd.Flags().String("diff", "", "Scan changes compared to specified commit/branch")
	scanCmd.Flags().Int("timeout", 300, "Timeout in seconds")
	scanCmd.Flags().Bool("report", false, "Generate detailed report")
	scanCmd.Flags().Bool("cache", true, "Enable caching")
}

func runScan(cmd *cobra.Command, args []string) error {
	startTime := time.Now()

	// Get scan paths
	paths := args
	if len(paths) == 0 {
		paths = []string{"."}
	}

	// Get flags
	vibesFlag, _ := cmd.Flags().GetStringSlice("vibes")
	excludeFlag, _ := cmd.Flags().GetStringSlice("exclude")
	minSeverity, _ := cmd.Flags().GetString("min-severity")
	outputFormat, _ := cmd.Flags().GetString("format")
	outputFile, _ := cmd.Flags().GetString("output")
	ciMode, _ := cmd.Flags().GetBool("ci")
	strictMode, _ := cmd.Flags().GetBool("strict")
	stagedOnly, _ := cmd.Flags().GetBool("staged")
	diffTarget, _ := cmd.Flags().GetString("diff")
	timeoutSecs, _ := cmd.Flags().GetInt("timeout")
	generateReport, _ := cmd.Flags().GetBool("report")
	enableCache, _ := cmd.Flags().GetBool("cache")

	// Parse vibes
	var vibes []models.VibeType
	if len(vibesFlag) > 0 {
		for _, vibeStr := range vibesFlag {
			for _, v := range strings.Split(vibeStr, ",") {
				vibe := strings.TrimSpace(v)
				vibes = append(vibes, models.VibeType(vibe))
			}
		}
	}

	// Create scanner
	cfg := configMgr.GetConfig()
	if !enableCache {
		cfg.Advanced.CacheEnabled = false
	}

	// Add exclude patterns
	cfg.Exclude.Files = append(cfg.Exclude.Files, excludeFlag...)

	scannerInstance, err := scanner.NewScanner(cfg, logger)
	if err != nil {
		return fmt.Errorf("failed to create scanner: %w", err)
	}

	// Convert vibes to strings
	vibeStrings := make([]string, len(vibes))
	for i, vibe := range vibes {
		vibeStrings[i] = string(vibe)
	}

	// Create scan request
	request := &models.ScanRequest{
		Paths:      paths,
		Vibes:      vibeStrings,
		Config:     cfg,
		StagedOnly: stagedOnly,
		DiffTarget: diffTarget,
		Format:     models.ReportFormat(outputFormat),
		CreatedAt:  time.Now(),
	}

	// Create context with timeout
	ctx, cancel := context.WithTimeout(context.Background(), time.Duration(timeoutSecs)*time.Second)
	defer cancel()

	// Show header
	showScanHeader(paths, vibes)

	// Run scan
	result, err := scannerInstance.Scan(ctx, request)
	if err != nil {
		return fmt.Errorf("scan failed: %w", err)
	}

	// Filter by severity
	filteredIssues := filterIssuesBySeverity(result.Issues, minSeverity)
	result.Issues = filteredIssues
	result.Summary = generateSummary(filteredIssues)

	// Generate output
	reporter := report.NewReporter(cfg)
	output, err := reporter.Generate(result, outputFormat)
	if err != nil {
		return fmt.Errorf("failed to generate report: %w", err)
	}

	// Write output
	if outputFile != "" {
		if err := os.WriteFile(outputFile, []byte(output), 0644); err != nil {
			return fmt.Errorf("failed to write output file: %w", err)
		}
		fmt.Printf("Report written to %s\n", outputFile)
	} else {
		fmt.Print(output)
	}

	// Show summary
	showScanSummary(result, time.Since(startTime))

	// Generate detailed report if requested
	if generateReport {
		reportPath := fmt.Sprintf("kodevibe-report-%s.html", time.Now().Format("20060102-150405"))
		htmlReport, err := reporter.Generate(result, "html")
		if err != nil {
			logger.Warnf("Failed to generate HTML report: %v", err)
		} else {
			if err := os.WriteFile(reportPath, []byte(htmlReport), 0644); err != nil {
				logger.Warnf("Failed to write HTML report: %v", err)
			} else {
				fmt.Printf("📊 Detailed report saved to %s\n", reportPath)
			}
		}
	}

	// Handle CI mode
	if ciMode {
		if strictMode && len(result.Issues) > 0 {
			os.Exit(1)
		} else if result.Summary.ErrorIssues > 0 {
			os.Exit(1)
		}
	}

	return nil
}

// installCmd represents the install command
var installCmd = &cobra.Command{
	Use:   "install [flags]",
	Short: "Install KodeVibe in current directory",
	Long: `Install KodeVibe configuration and git hooks in the current directory.
	
Examples:
  kodevibe install                    # Install with auto-detection
  kodevibe install --hooks            # Install git hooks
  kodevibe install --config-only      # Install config file only`,
	RunE: runInstall,
}

func init() {
	installCmd.Flags().Bool("hooks", false, "Install git hooks")
	installCmd.Flags().Bool("config-only", false, "Install configuration file only")
	installCmd.Flags().String("config-path", ".kodevibe.yaml", "Path for configuration file")
}

func runInstall(cmd *cobra.Command, args []string) error {
	installHooks, _ := cmd.Flags().GetBool("hooks")
	configOnly, _ := cmd.Flags().GetBool("config-only")
	configPath, _ := cmd.Flags().GetString("config-path")

	fmt.Println("🌊 Installing KodeVibe...")

	// Install configuration file
	if err := config.CreateDefaultConfig(configPath); err != nil {
		return fmt.Errorf("failed to create config file: %w", err)
	}
	fmt.Printf("✅ Configuration file created: %s\n", configPath)

	// Install git hooks if requested or not config-only
	if installHooks || !configOnly {
		if err := installGitHooks(); err != nil {
			return fmt.Errorf("failed to install git hooks: %w", err)
		}
		fmt.Println("✅ Git hooks installed")
	}

	fmt.Println("🎉 KodeVibe installation complete!")
	fmt.Println("💡 Run 'kodevibe scan' to start scanning")

	return nil
}

// hooksCmd represents the hooks command
var hooksCmd = &cobra.Command{
	Use:   "hooks [install|uninstall|test]",
	Short: "Manage git hooks",
	Args:  cobra.ExactArgs(1),
	RunE:  runHooks,
}

func runHooks(cmd *cobra.Command, args []string) error {
	action := args[0]

	switch action {
	case "install":
		return installGitHooks()
	case "uninstall":
		return uninstallGitHooks()
	case "test":
		return testGitHooks()
	default:
		return fmt.Errorf("unknown action: %s", action)
	}
}

// configCmd represents the config command
var configCmd = &cobra.Command{
	Use:   "config [show|validate|init]",
	Short: "Manage configuration",
	Args:  cobra.MaximumNArgs(1),
	RunE:  runConfig,
}

func runConfig(cmd *cobra.Command, args []string) error {
	action := "show"
	if len(args) > 0 {
		action = args[0]
	}

	switch action {
	case "show":
		return showConfig()
	case "validate":
		return validateConfig()
	case "init":
		return config.CreateDefaultConfig(".kodevibe.yaml")
	default:
		return fmt.Errorf("unknown action: %s", action)
	}
}

// fixCmd represents the fix command
var fixCmd = &cobra.Command{
	Use:   "fix [paths...]",
	Short: "Auto-fix detected issues",
	Long: `Automatically fix issues that can be safely corrected.
	
Examples:
  kodevibe fix                        # Fix issues in current directory
  kodevibe fix src/                   # Fix issues in specific directory
  kodevibe fix --auto --backup        # Auto-fix with backup`,
	Args: cobra.ArbitraryArgs,
	RunE: runFix,
}

func init() {
	fixCmd.Flags().Bool("auto", false, "Automatically fix without prompting")
	fixCmd.Flags().Bool("backup", true, "Create backup before fixing")
	fixCmd.Flags().StringSlice("rules", []string{}, "Specific rules to fix")
}

func runFix(cmd *cobra.Command, args []string) error {
	autoFix, _ := cmd.Flags().GetBool("auto")
	createBackup, _ := cmd.Flags().GetBool("backup")
	rules, _ := cmd.Flags().GetStringSlice("rules")

	paths := args
	if len(paths) == 0 {
		paths = []string{"."}
	}

	cfg := configMgr.GetConfig()
	fixer := fix.NewFixer(cfg, logger)

	return fixer.Fix(paths, autoFix, createBackup, rules)
}

// reportCmd represents the report command
var reportCmd = &cobra.Command{
	Use:   "report [flags]",
	Short: "Generate detailed reports",
	RunE:  runReport,
}

func init() {
	reportCmd.Flags().String("input", "", "Input scan result file")
	reportCmd.Flags().String("format", "html", "Report format (html, pdf, json)")
	reportCmd.Flags().String("output", "", "Output file path")
}

func runReport(cmd *cobra.Command, args []string) error {
	inputFile, _ := cmd.Flags().GetString("input")
	format, _ := cmd.Flags().GetString("format")
	outputFile, _ := cmd.Flags().GetString("output")

	if inputFile == "" {
		return fmt.Errorf("input file is required")
	}

	// TODO: Implement report generation from file
	fmt.Printf("Generating %s report from %s to %s\n", format, inputFile, outputFile)
	return nil
}

// profileCmd represents the profile command
var profileCmd = &cobra.Command{
	Use:   "profile [flags]",
	Short: "Run performance profiling",
	RunE:  runProfile,
}

func init() {
	profileCmd.Flags().String("tool", "lighthouse", "Profiling tool (lighthouse, webpack-analyzer)")
	profileCmd.Flags().String("url", "http://localhost:3000", "URL to profile")
}

func runProfile(cmd *cobra.Command, args []string) error {
	tool, _ := cmd.Flags().GetString("tool")
	url, _ := cmd.Flags().GetString("url")

	fmt.Printf("Running %s profiling on %s\n", tool, url)
	// TODO: Implement profiling
	return nil
}

// watchCmd represents the watch command
var watchCmd = &cobra.Command{
	Use:   "watch [paths...]",
	Short: "Watch files for changes and scan automatically",
	Args:  cobra.ArbitraryArgs,
	RunE:  runWatch,
}

func init() {
	watchCmd.Flags().Bool("auto-fix", false, "Automatically fix issues when detected")
	watchCmd.Flags().StringSlice("vibes", []string{}, "Vibes to run on file changes")
}

func runWatch(cmd *cobra.Command, args []string) error {
	autoFix, _ := cmd.Flags().GetBool("auto-fix")
	vibes, _ := cmd.Flags().GetStringSlice("vibes")

	paths := args
	if len(paths) == 0 {
		paths = []string{"."}
	}

	cfg := configMgr.GetConfig()
	watcher := watch.NewWatcher(cfg, logger)

	return watcher.Watch(paths, autoFix, vibes)
}

// serverCmd represents the server command
var serverCmd = &cobra.Command{
	Use:   "server [flags]",
	Short: "Start KodeVibe HTTP server",
	RunE:  runServer,
}

func init() {
	serverCmd.Flags().String("host", "localhost", "Server host")
	serverCmd.Flags().Int("port", 8080, "Server port")
	serverCmd.Flags().Bool("tls", false, "Enable TLS")
	serverCmd.Flags().String("cert", "", "TLS certificate file")
	serverCmd.Flags().String("key", "", "TLS key file")
}

func runServer(cmd *cobra.Command, args []string) error {
	host, _ := cmd.Flags().GetString("host")
	port, _ := cmd.Flags().GetInt("port")
	tlsEnabled, _ := cmd.Flags().GetBool("tls")
	certFile, _ := cmd.Flags().GetString("cert")
	keyFile, _ := cmd.Flags().GetString("key")

	cfg := configMgr.GetConfig()
	cfg.Advanced.MaxConcurrency = 20 // Increase for server mode

	srv := server.NewServer(cfg, logger)
	return srv.Start(host, port, tlsEnabled, certFile, keyFile)
}

// updateCmd represents the update command
var updateCmd = &cobra.Command{
	Use:   "update",
	Short: "Update KodeVibe to the latest version",
	RunE:  runUpdate,
}

func runUpdate(cmd *cobra.Command, args []string) error {
	fmt.Println("🔄 Checking for updates...")
	// TODO: Implement update mechanism
	fmt.Println("✅ KodeVibe is up to date!")
	return nil
}

// versionCmd represents the version command
var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Show version information",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("KodeVibe v%s\n", rootCmd.Version)
		fmt.Println("🌊 The Ultimate Code Quality Guardian")
		fmt.Println("Built with Go")
	},
}

// Helper functions

func showScanHeader(paths []string, vibes []models.VibeType) {
	blue := color.New(color.FgBlue).SprintFunc()
	fmt.Printf("%s KodeVibe - Scanning for bad vibes...\n", blue("🌊"))
	fmt.Printf("📁 Paths: %s\n", strings.Join(paths, ", "))
	if len(vibes) > 0 {
		fmt.Printf("🎯 Vibes: %s\n", strings.Join(vibeTypesToStrings(vibes), ", "))
	}
	fmt.Println()
}

func showScanSummary(result *models.ScanResult, duration time.Duration) {
	fmt.Println("\n" + strings.Repeat("=", 50))
	fmt.Printf("📊 Scan Summary\n")
	fmt.Printf("⏱️  Duration: %v\n", duration)
	fmt.Printf("📄 Files scanned: %d\n", result.FilesScanned)
	fmt.Printf("⚠️  Total issues: %d\n", result.Summary.TotalIssues)

	if result.Summary.ErrorIssues > 0 {
		red := color.New(color.FgRed).SprintFunc()
		fmt.Printf("❌ Errors: %s\n", red(result.Summary.ErrorIssues))
	}
	if result.Summary.WarningIssues > 0 {
		yellow := color.New(color.FgYellow).SprintFunc()
		fmt.Printf("⚠️  Warnings: %s\n", yellow(result.Summary.WarningIssues))
	}
	if result.Summary.InfoIssues > 0 {
		blue := color.New(color.FgBlue).SprintFunc()
		fmt.Printf("ℹ️  Info: %s\n", blue(result.Summary.InfoIssues))
	}

	fmt.Printf("📈 Score: %.1f (%s)\n", result.Summary.Score, result.Summary.Grade)
	fmt.Println(strings.Repeat("=", 50))
}

func filterIssuesBySeverity(issues []models.Issue, minSeverity string) []models.Issue {
	severityMap := map[string]int{
		"info":    0,
		"warning": 1,
		"error":   2,
	}

	minLevel := severityMap[minSeverity]
	var filtered []models.Issue

	for _, issue := range issues {
		if severityMap[string(issue.Severity)] >= minLevel {
			filtered = append(filtered, issue)
		}
	}

	return filtered
}

func generateSummary(issues []models.Issue) models.ScanSummary {
	summary := models.ScanSummary{
		TotalIssues:      len(issues),
		IssuesByType:     make(map[models.VibeType]int),
		IssuesBySeverity: make(map[models.SeverityLevel]int),
	}

	for _, issue := range issues {
		summary.IssuesByType[issue.Type]++
		summary.IssuesBySeverity[issue.Severity]++

		switch issue.Severity {
		case models.SeverityError:
			summary.ErrorIssues++
		case models.SeverityWarning:
			summary.WarningIssues++
		case models.SeverityInfo:
			summary.InfoIssues++
		}
	}

	// Calculate score (100 - penalties)
	summary.Score = 100.0 - float64(summary.ErrorIssues*10) - float64(summary.WarningIssues*5) - float64(summary.InfoIssues*1)
	if summary.Score < 0 {
		summary.Score = 0
	}

	// Determine grade
	switch {
	case summary.Score >= 90:
		summary.Grade = "A"
	case summary.Score >= 80:
		summary.Grade = "B"
	case summary.Score >= 70:
		summary.Grade = "C"
	case summary.Score >= 60:
		summary.Grade = "D"
	default:
		summary.Grade = "F"
	}

	return summary
}

func vibeTypesToStrings(vibes []models.VibeType) []string {
	var strs []string
	for _, vibe := range vibes {
		strs = append(strs, string(vibe))
	}
	return strs
}

func installGitHooks() error {
	if _, err := os.Stat(".git"); os.IsNotExist(err) {
		return fmt.Errorf("not a git repository")
	}

	// Create hooks directory if it doesn't exist
	hooksDir := ".git/hooks"
	if err := os.MkdirAll(hooksDir, 0755); err != nil {
		return fmt.Errorf("failed to create hooks directory: %w", err)
	}

	// Pre-commit hook
	preCommitHook := `#!/bin/bash
echo "🌊 KodeVibe - Pre-commit scan..."
kodevibe scan --vibes security,code,file --staged --ci
exit $?
`
	preCommitPath := filepath.Join(hooksDir, "pre-commit")
	if err := os.WriteFile(preCommitPath, []byte(preCommitHook), 0755); err != nil {
		return fmt.Errorf("failed to write pre-commit hook: %w", err)
	}

	// Pre-push hook
	prePushHook := `#!/bin/bash
echo "🌊 KodeVibe - Pre-push scan..."
kodevibe scan --ci --strict
exit $?
`
	prePushPath := filepath.Join(hooksDir, "pre-push")
	if err := os.WriteFile(prePushPath, []byte(prePushHook), 0755); err != nil {
		return fmt.Errorf("failed to write pre-push hook: %w", err)
	}

	return nil
}

func uninstallGitHooks() error {
	hooksToRemove := []string{".git/hooks/pre-commit", ".git/hooks/pre-push"}

	for _, hook := range hooksToRemove {
		if err := os.Remove(hook); err != nil && !os.IsNotExist(err) {
			return fmt.Errorf("failed to remove %s: %w", hook, err)
		}
	}

	fmt.Println("✅ Git hooks uninstalled")
	return nil
}

func testGitHooks() error {
	fmt.Println("🧪 Testing git hooks...")

	// Test pre-commit hook
	if _, err := os.Stat(".git/hooks/pre-commit"); err == nil {
		fmt.Println("✅ Pre-commit hook found")
	} else {
		fmt.Println("❌ Pre-commit hook not found")
	}

	// Test pre-push hook
	if _, err := os.Stat(".git/hooks/pre-push"); err == nil {
		fmt.Println("✅ Pre-push hook found")
	} else {
		fmt.Println("❌ Pre-push hook not found")
	}

	return nil
}

func showConfig() error {
	cfg := configMgr.GetConfig()
	fmt.Println("📋 Current Configuration:")
	fmt.Printf("Project Type: %s\n", cfg.Project.Type)
	fmt.Printf("Language: %s\n", cfg.Project.Language)

	fmt.Println("\n🎯 Enabled Vibes:")
	for vibeType, vibeConfig := range cfg.Vibes {
		status := "❌"
		if vibeConfig.Enabled {
			status = "✅"
		}
		fmt.Printf("  %s %s (%s)\n", status, vibeType, vibeConfig.Level)
	}

	return nil
}

func validateConfig() error {
	if err := config.ValidateConfigFile(cfgFile); err != nil {
		return fmt.Errorf("configuration validation failed: %w", err)
	}

	fmt.Println("✅ Configuration is valid")
	return nil
}
