# Print an optspec for argparse to handle cmd's options that are independent of any subcommand.
function __fish_sl_daemon_global_optspecs
    string join \n url= h/help V/version
end

function __fish_sl_daemon_needs_command
    # Figure out if the current invocation already has a command.
    set -l cmd (commandline -opc)
    set -e cmd[1]
    argparse -s (__fish_sl_daemon_global_optspecs) -- $cmd 2>/dev/null
    or return
    if set -q argv[1]
        # Also print the command, so this can be used to figure out what it is.
        echo $argv[1]
        return 1
    end
    return 0
end

function __fish_sl_daemon_using_subcommand
    set -l cmd (__fish_sl_daemon_needs_command)
    test -z "$cmd"
    and return 1
    contains -- $cmd[1] $argv
end

complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -s V -l version -d 'Print version'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "serve" -d 'Start the file-watcher daemon'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "status" -d 'Check daemon status (exit 0 = running, exit 1 = not running)'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "list" -d 'List compiled OKF bundle paths (one per line)'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "tail" -d 'Stream new bundle paths as they arrive (SSE). Press Ctrl+C to stop'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "export" -d 'Export bundle metadata as CSV, Markdown, or JSON'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "summary" -d 'Print aggregate statistics across all bundles'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "tag" -d 'Manage tags on OKF bundle files'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "archive" -d 'Archive bundles older than a given date by gzipping them'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "restore" -d 'Restore a previously archived bundle by decompressing it'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "replay" -d 'Replay a compiled OKF bundle, streaming its entities in chronological order.  Connects to the running daemon\'s SSE endpoint unless `--bundle` points to a local file'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "validate" -d 'Validate an OKF bundle on disk against ingest rules'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "search" -d 'Search / filter bundles by date, model, token count, or tags'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "completions" -d 'Generate shell completion scripts to stdout'
complete -c sl-daemon -n "__fish_sl_daemon_needs_command" -f -a "help" -d 'Print this message or the help of the given subcommand(s)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -l watch -d 'Directory to watch for `*.jsonl` session transcripts' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -l out -d 'Directory to write `<session-id>.okf.json` files into' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -l http-bind -d 'Address to bind the HTTP server on (e.g. `127.0.0.1:8080`). Loopback keeps optional API-key trust; non-loopback requires `SL_API_KEY`. Pass `off` to disable the HTTP server entirely' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -l memory-db -d 'SQLite database for durable episodic memory (`SL_MEMORY_DB`). Requires `sl-daemon` built with `--features sqlite`' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -l once -d 'Do a single sweep of `--watch` then exit (CI / cron-friendly)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand serve" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand status" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand status" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand list" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand list" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tail" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tail" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand export" -l format -d 'Output format: csv | md | json  (default: csv)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand export" -l out -d 'Write output to this file; defaults to stdout' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand export" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand export" -s h -l help -d 'Print help (see more with \'--help\')'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand summary" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand summary" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -f -a "add" -d 'Add one or more tags to a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -f -a "remove" -d 'Remove one or more tags from a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -f -a "list" -d 'List current tags on a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -f -a "search" -d 'Search a directory for bundles that carry a specific tag'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and not __fish_seen_subcommand_from add remove list search help" -f -a "help" -d 'Print this message or the help of the given subcommand(s)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from add" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from add" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from remove" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from remove" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from list" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from list" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from search" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from search" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from help" -f -a "add" -d 'Add one or more tags to a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from help" -f -a "remove" -d 'Remove one or more tags from a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from help" -f -a "list" -d 'List current tags on a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from help" -f -a "search" -d 'Search a directory for bundles that carry a specific tag'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand tag; and __fish_seen_subcommand_from help" -f -a "help" -d 'Print this message or the help of the given subcommand(s)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand archive" -l before -d 'Archive bundles with created_at strictly before this date (YYYY-MM-DD)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand archive" -l data-dir -d 'Directory containing the bundle JSON files (and where the archive sub-tree will be created)' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand archive" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand archive" -l dry-run -d 'Print what would be archived without touching the filesystem'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand archive" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand restore" -l data-dir -d 'Directory that contains the `archive/` sub-tree' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand restore" -l out -d 'Directory to write the restored `.okf.json` file into. Defaults to `<data_dir>`' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand restore" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand restore" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand replay" -l speed -d 'Playback speed multiplier (default 1.0).  `--speed 2.0` replays at 2├ù real-time' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand replay" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand replay" -l no-stream -d 'Print all entities at once without any delay'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand replay" -s h -l help -d 'Print help'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand validate" -l data-dir -d 'Directory containing the `.okf.json` files' -r -F
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand validate" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand validate" -s h -l help -d 'Print help (see more with \'--help\')'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l since -d 'Include only bundles created on or after this date (YYYY-MM-DD)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l until -d 'Include only bundles created on or before this date (YYYY-MM-DD)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l model -d 'Include only bundles whose model name contains this substring (case-insensitive)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l min-tokens -d 'Include only bundles with at least this many tokens' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l tag -d 'Include only bundles that carry this tag (repeat for AND logic)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l limit -d 'Maximum number of results to return (default: 50)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l format -d 'Output format: text | json | csv  (default: text)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand search" -s h -l help -d 'Print help (see more with \'--help\')'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand completions" -l url -d 'Base URL of the daemon HTTP server (used by status / list / tail)' -r
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand completions" -s h -l help -d 'Print help (see more with \'--help\')'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "serve" -d 'Start the file-watcher daemon'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "status" -d 'Check daemon status (exit 0 = running, exit 1 = not running)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "list" -d 'List compiled OKF bundle paths (one per line)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "tail" -d 'Stream new bundle paths as they arrive (SSE). Press Ctrl+C to stop'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "export" -d 'Export bundle metadata as CSV, Markdown, or JSON'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "summary" -d 'Print aggregate statistics across all bundles'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "tag" -d 'Manage tags on OKF bundle files'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "archive" -d 'Archive bundles older than a given date by gzipping them'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "restore" -d 'Restore a previously archived bundle by decompressing it'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "replay" -d 'Replay a compiled OKF bundle, streaming its entities in chronological order.  Connects to the running daemon\'s SSE endpoint unless `--bundle` points to a local file'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "validate" -d 'Validate an OKF bundle on disk against ingest rules'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "search" -d 'Search / filter bundles by date, model, token count, or tags'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "completions" -d 'Generate shell completion scripts to stdout'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and not __fish_seen_subcommand_from serve status list tail export summary tag archive restore replay validate search completions help" -f -a "help" -d 'Print this message or the help of the given subcommand(s)'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and __fish_seen_subcommand_from tag" -f -a "add" -d 'Add one or more tags to a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and __fish_seen_subcommand_from tag" -f -a "remove" -d 'Remove one or more tags from a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and __fish_seen_subcommand_from tag" -f -a "list" -d 'List current tags on a bundle'
complete -c sl-daemon -n "__fish_sl_daemon_using_subcommand help; and __fish_seen_subcommand_from tag" -f -a "search" -d 'Search a directory for bundles that carry a specific tag'
