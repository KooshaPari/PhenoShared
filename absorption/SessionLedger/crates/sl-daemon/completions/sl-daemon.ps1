
using namespace System.Management.Automation
using namespace System.Management.Automation.Language

Register-ArgumentCompleter -Native -CommandName 'sl-daemon' -ScriptBlock {
    param($wordToComplete, $commandAst, $cursorPosition)

    $commandElements = $commandAst.CommandElements
    $command = @(
        'sl-daemon'
        for ($i = 1; $i -lt $commandElements.Count; $i++) {
            $element = $commandElements[$i]
            if ($element -isnot [StringConstantExpressionAst] -or
                $element.StringConstantType -ne [StringConstantType]::BareWord -or
                $element.Value.StartsWith('-') -or
                $element.Value -eq $wordToComplete) {
                break
        }
        $element.Value
    }) -join ';'

    $completions = @(switch ($command) {
        'sl-daemon' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('-V', '-V ', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('--version', '--version', [CompletionResultType]::ParameterName, 'Print version')
            [CompletionResult]::new('serve', 'serve', [CompletionResultType]::ParameterValue, 'Start the file-watcher daemon')
            [CompletionResult]::new('status', 'status', [CompletionResultType]::ParameterValue, 'Check daemon status (exit 0 = running, exit 1 = not running)')
            [CompletionResult]::new('list', 'list', [CompletionResultType]::ParameterValue, 'List compiled OKF bundle paths (one per line)')
            [CompletionResult]::new('tail', 'tail', [CompletionResultType]::ParameterValue, 'Stream new bundle paths as they arrive (SSE). Press Ctrl+C to stop')
            [CompletionResult]::new('export', 'export', [CompletionResultType]::ParameterValue, 'Export bundle metadata as CSV, Markdown, or JSON')
            [CompletionResult]::new('summary', 'summary', [CompletionResultType]::ParameterValue, 'Print aggregate statistics across all bundles')
            [CompletionResult]::new('tag', 'tag', [CompletionResultType]::ParameterValue, 'Manage tags on OKF bundle files')
            [CompletionResult]::new('archive', 'archive', [CompletionResultType]::ParameterValue, 'Archive bundles older than a given date by gzipping them')
            [CompletionResult]::new('restore', 'restore', [CompletionResultType]::ParameterValue, 'Restore a previously archived bundle by decompressing it')
            [CompletionResult]::new('replay', 'replay', [CompletionResultType]::ParameterValue, 'Replay a compiled OKF bundle, streaming its entities in chronological order.  Connects to the running daemon''s SSE endpoint unless `--bundle` points to a local file')
            [CompletionResult]::new('validate', 'validate', [CompletionResultType]::ParameterValue, 'Validate an OKF bundle on disk against ingest rules')
            [CompletionResult]::new('search', 'search', [CompletionResultType]::ParameterValue, 'Search / filter bundles by date, model, token count, or tags')
            [CompletionResult]::new('completions', 'completions', [CompletionResultType]::ParameterValue, 'Generate shell completion scripts to stdout')
            [CompletionResult]::new('help', 'help', [CompletionResultType]::ParameterValue, 'Print this message or the help of the given subcommand(s)')
            break
        }
        'sl-daemon;serve' {
            [CompletionResult]::new('--watch', '--watch', [CompletionResultType]::ParameterName, 'Directory to watch for `*.jsonl` session transcripts')
            [CompletionResult]::new('--out', '--out', [CompletionResultType]::ParameterName, 'Directory to write `<session-id>.okf.json` files into')
            [CompletionResult]::new('--http-bind', '--http-bind', [CompletionResultType]::ParameterName, 'Address to bind the HTTP server on (e.g. `127.0.0.1:8080`). Loopback keeps optional API-key trust; non-loopback requires `SL_API_KEY`. Pass `off` to disable the HTTP server entirely')
            [CompletionResult]::new('--memory-db', '--memory-db', [CompletionResultType]::ParameterName, 'SQLite database for durable episodic memory (`SL_MEMORY_DB`). Requires `sl-daemon` built with `--features sqlite`')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('--once', '--once', [CompletionResultType]::ParameterName, 'Do a single sweep of `--watch` then exit (CI / cron-friendly)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;status' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;list' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;tail' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;export' {
            [CompletionResult]::new('--format', '--format', [CompletionResultType]::ParameterName, 'Output format: csv | md | json  (default: csv)')
            [CompletionResult]::new('--out', '--out', [CompletionResultType]::ParameterName, 'Write output to this file; defaults to stdout')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            break
        }
        'sl-daemon;summary' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;tag' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('add', 'add', [CompletionResultType]::ParameterValue, 'Add one or more tags to a bundle')
            [CompletionResult]::new('remove', 'remove', [CompletionResultType]::ParameterValue, 'Remove one or more tags from a bundle')
            [CompletionResult]::new('list', 'list', [CompletionResultType]::ParameterValue, 'List current tags on a bundle')
            [CompletionResult]::new('search', 'search', [CompletionResultType]::ParameterValue, 'Search a directory for bundles that carry a specific tag')
            [CompletionResult]::new('help', 'help', [CompletionResultType]::ParameterValue, 'Print this message or the help of the given subcommand(s)')
            break
        }
        'sl-daemon;tag;add' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;tag;remove' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;tag;list' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;tag;search' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;tag;help' {
            [CompletionResult]::new('add', 'add', [CompletionResultType]::ParameterValue, 'Add one or more tags to a bundle')
            [CompletionResult]::new('remove', 'remove', [CompletionResultType]::ParameterValue, 'Remove one or more tags from a bundle')
            [CompletionResult]::new('list', 'list', [CompletionResultType]::ParameterValue, 'List current tags on a bundle')
            [CompletionResult]::new('search', 'search', [CompletionResultType]::ParameterValue, 'Search a directory for bundles that carry a specific tag')
            [CompletionResult]::new('help', 'help', [CompletionResultType]::ParameterValue, 'Print this message or the help of the given subcommand(s)')
            break
        }
        'sl-daemon;tag;help;add' {
            break
        }
        'sl-daemon;tag;help;remove' {
            break
        }
        'sl-daemon;tag;help;list' {
            break
        }
        'sl-daemon;tag;help;search' {
            break
        }
        'sl-daemon;tag;help;help' {
            break
        }
        'sl-daemon;archive' {
            [CompletionResult]::new('--before', '--before', [CompletionResultType]::ParameterName, 'Archive bundles with created_at strictly before this date (YYYY-MM-DD)')
            [CompletionResult]::new('--data-dir', '--data-dir', [CompletionResultType]::ParameterName, 'Directory containing the bundle JSON files (and where the archive sub-tree will be created)')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('--dry-run', '--dry-run', [CompletionResultType]::ParameterName, 'Print what would be archived without touching the filesystem')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;restore' {
            [CompletionResult]::new('--data-dir', '--data-dir', [CompletionResultType]::ParameterName, 'Directory that contains the `archive/` sub-tree')
            [CompletionResult]::new('--out', '--out', [CompletionResultType]::ParameterName, 'Directory to write the restored `.okf.json` file into. Defaults to `<data_dir>`')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;replay' {
            [CompletionResult]::new('--speed', '--speed', [CompletionResultType]::ParameterName, 'Playback speed multiplier (default 1.0).  `--speed 2.0` replays at 2├ù real-time')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('--no-stream', '--no-stream', [CompletionResultType]::ParameterName, 'Print all entities at once without any delay')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help')
            break
        }
        'sl-daemon;validate' {
            [CompletionResult]::new('--data-dir', '--data-dir', [CompletionResultType]::ParameterName, 'Directory containing the `.okf.json` files')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            break
        }
        'sl-daemon;search' {
            [CompletionResult]::new('--since', '--since', [CompletionResultType]::ParameterName, 'Include only bundles created on or after this date (YYYY-MM-DD)')
            [CompletionResult]::new('--until', '--until', [CompletionResultType]::ParameterName, 'Include only bundles created on or before this date (YYYY-MM-DD)')
            [CompletionResult]::new('--model', '--model', [CompletionResultType]::ParameterName, 'Include only bundles whose model name contains this substring (case-insensitive)')
            [CompletionResult]::new('--min-tokens', '--min-tokens', [CompletionResultType]::ParameterName, 'Include only bundles with at least this many tokens')
            [CompletionResult]::new('--tag', '--tag', [CompletionResultType]::ParameterName, 'Include only bundles that carry this tag (repeat for AND logic)')
            [CompletionResult]::new('--limit', '--limit', [CompletionResultType]::ParameterName, 'Maximum number of results to return (default: 50)')
            [CompletionResult]::new('--format', '--format', [CompletionResultType]::ParameterName, 'Output format: text | json | csv  (default: text)')
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            break
        }
        'sl-daemon;completions' {
            [CompletionResult]::new('--url', '--url', [CompletionResultType]::ParameterName, 'Base URL of the daemon HTTP server (used by status / list / tail)')
            [CompletionResult]::new('-h', '-h', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            [CompletionResult]::new('--help', '--help', [CompletionResultType]::ParameterName, 'Print help (see more with ''--help'')')
            break
        }
        'sl-daemon;help' {
            [CompletionResult]::new('serve', 'serve', [CompletionResultType]::ParameterValue, 'Start the file-watcher daemon')
            [CompletionResult]::new('status', 'status', [CompletionResultType]::ParameterValue, 'Check daemon status (exit 0 = running, exit 1 = not running)')
            [CompletionResult]::new('list', 'list', [CompletionResultType]::ParameterValue, 'List compiled OKF bundle paths (one per line)')
            [CompletionResult]::new('tail', 'tail', [CompletionResultType]::ParameterValue, 'Stream new bundle paths as they arrive (SSE). Press Ctrl+C to stop')
            [CompletionResult]::new('export', 'export', [CompletionResultType]::ParameterValue, 'Export bundle metadata as CSV, Markdown, or JSON')
            [CompletionResult]::new('summary', 'summary', [CompletionResultType]::ParameterValue, 'Print aggregate statistics across all bundles')
            [CompletionResult]::new('tag', 'tag', [CompletionResultType]::ParameterValue, 'Manage tags on OKF bundle files')
            [CompletionResult]::new('archive', 'archive', [CompletionResultType]::ParameterValue, 'Archive bundles older than a given date by gzipping them')
            [CompletionResult]::new('restore', 'restore', [CompletionResultType]::ParameterValue, 'Restore a previously archived bundle by decompressing it')
            [CompletionResult]::new('replay', 'replay', [CompletionResultType]::ParameterValue, 'Replay a compiled OKF bundle, streaming its entities in chronological order.  Connects to the running daemon''s SSE endpoint unless `--bundle` points to a local file')
            [CompletionResult]::new('validate', 'validate', [CompletionResultType]::ParameterValue, 'Validate an OKF bundle on disk against ingest rules')
            [CompletionResult]::new('search', 'search', [CompletionResultType]::ParameterValue, 'Search / filter bundles by date, model, token count, or tags')
            [CompletionResult]::new('completions', 'completions', [CompletionResultType]::ParameterValue, 'Generate shell completion scripts to stdout')
            [CompletionResult]::new('help', 'help', [CompletionResultType]::ParameterValue, 'Print this message or the help of the given subcommand(s)')
            break
        }
        'sl-daemon;help;serve' {
            break
        }
        'sl-daemon;help;status' {
            break
        }
        'sl-daemon;help;list' {
            break
        }
        'sl-daemon;help;tail' {
            break
        }
        'sl-daemon;help;export' {
            break
        }
        'sl-daemon;help;summary' {
            break
        }
        'sl-daemon;help;tag' {
            [CompletionResult]::new('add', 'add', [CompletionResultType]::ParameterValue, 'Add one or more tags to a bundle')
            [CompletionResult]::new('remove', 'remove', [CompletionResultType]::ParameterValue, 'Remove one or more tags from a bundle')
            [CompletionResult]::new('list', 'list', [CompletionResultType]::ParameterValue, 'List current tags on a bundle')
            [CompletionResult]::new('search', 'search', [CompletionResultType]::ParameterValue, 'Search a directory for bundles that carry a specific tag')
            break
        }
        'sl-daemon;help;tag;add' {
            break
        }
        'sl-daemon;help;tag;remove' {
            break
        }
        'sl-daemon;help;tag;list' {
            break
        }
        'sl-daemon;help;tag;search' {
            break
        }
        'sl-daemon;help;archive' {
            break
        }
        'sl-daemon;help;restore' {
            break
        }
        'sl-daemon;help;replay' {
            break
        }
        'sl-daemon;help;validate' {
            break
        }
        'sl-daemon;help;search' {
            break
        }
        'sl-daemon;help;completions' {
            break
        }
        'sl-daemon;help;help' {
            break
        }
    })

    $completions.Where{ $_.CompletionText -like "$wordToComplete*" } |
        Sort-Object -Property ListItemText
}
