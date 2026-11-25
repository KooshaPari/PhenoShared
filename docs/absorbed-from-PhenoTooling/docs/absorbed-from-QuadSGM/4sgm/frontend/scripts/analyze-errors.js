#!/usr/bin/env node

/**
 * Error Analysis Script
 *
 * Processes TypeScript diagnostics and categorizes errors for targeted remediation.
 * Reads from stdin and outputs categorized analysis.
 *
 * Usage:
 *   npm run tsc -- --noEmit 2>&1 | node scripts/analyze-errors.js
 *   tsc --noEmit > errors.txt && node scripts/analyze-errors.js < errors.txt
 */

const readline = require("readline");
const fs = require("fs");
const path = require("path");

/**
 * Error categories matching the audit system
 */
const CATEGORIES = {
  UNUSED_IMPORTS: "unused_imports",
  TYPE_MISMATCH: "type_mismatch",
  MISSING_DECLARATION: "missing_declaration",
  IMPLICIT_ANY: "implicit_any",
  UNUSED_VARIABLES: "unused_variables",
  MISSING_RETURN_TYPE: "missing_return_type",
  NON_NULL_ASSERTION: "non_null_assertion",
  DEPRECATED_API: "deprecated_api",
  IMPORT_ERRORS: "import_errors",
  UNKNOWN: "unknown",
};

/**
 * Severity levels
 */
const SEVERITY = {
  CRITICAL: "critical",
  HIGH: "high",
  MEDIUM: "medium",
  LOW: "low",
};

/**
 * Pattern matcher for error categorization
 */
class ErrorPatternMatcher {
  static categorizeError(message, code) {
    // Unused imports
    if (
      message.includes("is declared but never used") ||
      message.includes("Unused property")
    ) {
      return {
        category: CATEGORIES.UNUSED_IMPORTS,
        severity: SEVERITY.LOW,
        suggestion: "Remove unused import",
      };
    }

    // Type mismatch
    if (
      message.includes("is not assignable to type") ||
      message.includes("Type") ||
      message.includes("is not compatible with")
    ) {
      return {
        category: CATEGORIES.TYPE_MISMATCH,
        severity: SEVERITY.HIGH,
        suggestion: "Review and align type definitions",
      };
    }

    // Missing declaration
    if (
      message.includes("Cannot find name") ||
      message.includes("is not defined") ||
      message.includes("Property") && message.includes("does not exist")
    ) {
      return {
        category: CATEGORIES.MISSING_DECLARATION,
        severity: SEVERITY.CRITICAL,
        suggestion: "Add missing import or type declaration",
      };
    }

    // Implicit any
    if (
      message.includes("implicitly has type") ||
      message.includes("Parameter implicitly has")
    ) {
      return {
        category: CATEGORIES.IMPLICIT_ANY,
        severity: SEVERITY.MEDIUM,
        suggestion: "Add explicit type annotation",
      };
    }

    // Unused variables
    if (
      message.includes("is declared but never used") &&
      message.includes("variable")
    ) {
      return {
        category: CATEGORIES.UNUSED_VARIABLES,
        severity: SEVERITY.LOW,
        suggestion: "Remove unused variable or use it",
      };
    }

    // Missing return type
    if (
      message.includes("Missing return type") ||
      message.includes("return type annotation")
    ) {
      return {
        category: CATEGORIES.MISSING_RETURN_TYPE,
        severity: SEVERITY.MEDIUM,
        suggestion: "Add explicit return type to function",
      };
    }

    // Non-null assertion
    if (message.includes("Object is possibly")) {
      return {
        category: CATEGORIES.NON_NULL_ASSERTION,
        severity: SEVERITY.MEDIUM,
        suggestion: "Add null check or use optional chaining",
      };
    }

    // Import errors
    if (
      message.includes("Cannot find module") ||
      message.includes("Module not found")
    ) {
      return {
        category: CATEGORIES.IMPORT_ERRORS,
        severity: SEVERITY.CRITICAL,
        suggestion: "Verify file path and ensure module exists",
      };
    }

    return {
      category: CATEGORIES.UNKNOWN,
      severity: SEVERITY.MEDIUM,
      suggestion: "Manual review required",
    };
  }
}

/**
 * Parse TypeScript diagnostic line
 * Format: "file.ts(line,col): error TS####: message"
 */
function parseDiagnostic(line) {
  const match = line.match(
    /^(.+?)\((\d+),(\d+)\):\s+(error|warning)\s+TS(\d+):\s+(.+)$/
  );

  if (!match) return null;

  const [, filePath, lineNum, colNum, type, code, message] = match;

  const { category, severity, suggestion } = ErrorPatternMatcher.categorizeError(
    message,
    code
  );

  return {
    filePath,
    line: parseInt(lineNum, 10),
    column: parseInt(colNum, 10),
    type,
    code: `TS${code}`,
    message,
    category,
    severity,
    suggestion,
  };
}

/**
 * Analyze error collection and generate summary
 */
function analyzeErrors(errors) {
  const summary = {
    total: errors.length,
    bySeverity: {
      [SEVERITY.CRITICAL]: 0,
      [SEVERITY.HIGH]: 0,
      [SEVERITY.MEDIUM]: 0,
      [SEVERITY.LOW]: 0,
    },
    byCategory: {},
    byFile: {},
    topFiles: [],
    suggestions: new Set(),
  };

  for (const error of errors) {
    // Count by severity
    summary.bySeverity[error.severity]++;

    // Count by category
    if (!summary.byCategory[error.category]) {
      summary.byCategory[error.category] = 0;
    }
    summary.byCategory[error.category]++;

    // Count by file
    if (!summary.byFile[error.filePath]) {
      summary.byFile[error.filePath] = 0;
    }
    summary.byFile[error.filePath]++;

    // Collect suggestions
    if (error.suggestion) {
      summary.suggestions.add(error.suggestion);
    }
  }

  // Get top problematic files
  summary.topFiles = Object.entries(summary.byFile)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20)
    .map(([file, count]) => ({ file, count }));

  // Convert set to array
  summary.suggestions = Array.from(summary.suggestions);

  return summary;
}

/**
 * Format report as text
 */
function formatTextReport(errors, summary) {
  const lines = [];

  lines.push("═".repeat(80));
  lines.push("TypeScript Error Analysis Report");
  lines.push("═".repeat(80));
  lines.push("");

  // Summary
  lines.push("SUMMARY");
  lines.push("-".repeat(80));
  lines.push(`Total Errors: ${summary.total}`);
  lines.push("");
  lines.push("By Severity:");
  for (const [severity, count] of Object.entries(summary.bySeverity)) {
    if (count > 0) {
      lines.push(`  ${severity.toUpperCase()}: ${count}`);
    }
  }
  lines.push("");

  // By Category
  lines.push("By Category:");
  for (const [category, count] of Object.entries(summary.byCategory).sort(
    (a, b) => b[1] - a[1]
  )) {
    lines.push(`  ${category}: ${count}`);
  }
  lines.push("");

  // Top problematic files
  lines.push("Top Problematic Files:");
  for (const { file, count } of summary.topFiles.slice(0, 10)) {
    lines.push(`  ${count.toString().padStart(4)} - ${file}`);
  }
  lines.push("");

  // Recommendations
  lines.push("RECOMMENDATIONS");
  lines.push("-".repeat(80));
  for (const suggestion of summary.suggestions.slice(0, 5)) {
    lines.push(`• ${suggestion}`);
  }
  lines.push("");

  // Critical errors (first 10)
  const criticalErrors = errors
    .filter((e) => e.severity === SEVERITY.CRITICAL)
    .slice(0, 10);

  if (criticalErrors.length > 0) {
    lines.push("CRITICAL ERRORS (must fix first)");
    lines.push("-".repeat(80));
    for (const error of criticalErrors) {
      lines.push(`${error.filePath}:${error.line}:${error.column}`);
      lines.push(`  ${error.code} - ${error.message}`);
      lines.push("");
    }
  }

  return lines.join("\n");
}

/**
 * Format report as JSON
 */
function formatJsonReport(errors, summary) {
  return {
    summary,
    errors: errors.slice(0, 100), // Limit to first 100 for readability
    topErrorsByCategory: Object.fromEntries(
      Object.entries(
        errors.reduce((acc, error) => {
          if (!acc[error.category]) {
            acc[error.category] = [];
          }
          acc[error.category].push(error);
          return acc;
        }, {})
      ).map(([cat, errs]) => [cat, errs.slice(0, 5)])
    ),
  };
}

/**
 * Main analysis function
 */
async function main() {
  const errors = [];
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false,
  });

  console.error("Reading diagnostic input...");

  for await (const line of rl) {
    if (!line.trim()) continue;

    const error = parseDiagnostic(line);
    if (error) {
      errors.push(error);
    }
  }

  console.error(`Processed ${errors.length} errors\n`);

  // Generate analysis
  const summary = analyzeErrors(errors);

  // Output text report to console
  console.log(formatTextReport(errors, summary));

  // Output JSON report to file
  const jsonReport = formatJsonReport(errors, summary);
  const reportPath = path.join(process.cwd(), "audit-report.json");

  fs.writeFileSync(reportPath, JSON.stringify(jsonReport, null, 2));
  console.error(`\n✓ JSON report written to: ${reportPath}`);

  // Also save summary
  const summaryPath = path.join(process.cwd(), "audit-summary.json");
  fs.writeFileSync(summaryPath, JSON.stringify(summary, null, 2));
  console.error(`✓ Summary written to: ${summaryPath}`);

  // Exit with appropriate code
  process.exit(summary.bySeverity.critical > 0 ? 1 : 0);
}

// Run analysis
main().catch((error) => {
  console.error("Analysis failed:", error);
  process.exit(1);
});
