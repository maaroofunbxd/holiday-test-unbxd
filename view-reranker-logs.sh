#!/bin/bash

# Helper script to view saved reranker logs

LOG_DIR="./reranker-logs"

if [ ! -d "$LOG_DIR" ]; then
    echo "No logs directory found at: $LOG_DIR"
    exit 1
fi

echo "=== Saved Reranker Logs ==="
echo ""

# List all saved log files with details
if [ -z "$(ls -A $LOG_DIR 2>/dev/null)" ]; then
    echo "No log files saved yet."
    exit 0
fi

echo "Available log files:"
echo ""

ls -lh "$LOG_DIR"/*.log 2>/dev/null | awk '{
    printf "%s %s %s %-50s\n", $6, $7, $8, $9
}' | sort -r

echo ""
echo "Total files: $(ls -1 "$LOG_DIR"/*.log 2>/dev/null | wc -l | tr -d ' ')"
echo "Total size: $(du -sh "$LOG_DIR" 2>/dev/null | awk '{print $1}')"
echo ""

# Show usage
echo "Usage:"
echo "  View a specific log:  cat $LOG_DIR/<filename>"
echo "  View latest log:      ls -t $LOG_DIR/*.log | head -1 | xargs cat"
echo "  Search all logs:      grep 'pattern' $LOG_DIR/*.log"
echo "  Count lines by pod:   for f in $LOG_DIR/*.log; do echo \$f: \$(wc -l < \$f); done"

