#!/bin/bash
# profiler.sh - Unified profiler launcher

CMD="${1:-help}"

case "$CMD" in
    quick)
        bash bin/all_metrics.sh "${2:-codex}" "${3:-reports}"
        ;;
    full)
        bash bin/all_metrics.sh "${2:-codex}" "${3:-reports}"
        ;;
    network)
        bash bin/network_profiler.sh "${2:-codex}" "${3:-reports}"
        ;;
    disk)
        bash bin/disk_profiler.sh "${2:-codex}" "${3:-reports}"
        ;;
    audit)
        bash bin/full_system_audit.sh "${2:-codex}" "${3:-reports}"
        ;;
    complexity)
        python3 bin/complexity_analyzer.py "${2:-.}" "${3:-python}"
        ;;
    all)
        echo "Running all profilers..."
        bash bin/all_metrics.sh "${2:-codex}" "${3:-reports}"
        bash bin/network_profiler.sh "${2:-codex}" "${3:-reports}"
        bash bin/disk_profiler.sh "${2:-codex}" "${3:-reports}"
        bash bin/full_system_audit.sh "${2:-codex}" "${3:-reports}"
        echo "All profilers complete!"
        ;;
    continuous)
        python3 bin/continuous_profiler.py "${2:-codex}"
        ;;
    charts)
        python3 bin/generate_charts.py "${2:-reports}"/*.csv
        ;;
    help|--help|-h)
        echo "Usage: ./profiler.sh <command> [target] [output_dir]"
        echo ""
        echo "Commands:"
        echo "  quick      - Quick system metrics"
        echo "  full      - Full metrics (default)"
        echo "  network    - Network profiling"
        echo "  disk      - Disk I/O profiling"
        echo "  audit     - Complete system audit"
        echo "  complexity - Code complexity analysis"
        echo "  all       - Run all profilers"
        echo "  continuous - Continuous monitoring"
        echo "  charts     - Generate charts from CSV"
        echo ""
        echo "Examples:"
        echo "  ./profiler.sh quick codex"
        echo "  ./profiler.sh all thegent"
        echo "  ./profiler.sh complexity . rust"
        ;;
    *)
        echo "Unknown command: $CMD"
        echo "Run './profiler.sh help' for usage"
        ;;
esac
