#!/bin/bash
# Watch pod resource usage with current/limit ratios
# Usage: ./watch-pods.sh [interval_seconds]

INTERVAL=${1:-5}

watch -n "$INTERVAL" "kubectl top pods -l'algo in (personalization,ranking)' --no-headers | \
  awk 'BEGIN {printf \"%-40s %-20s %-20s\n\", \"POD\", \"CPU (current)\", \"MEMORY (current)\"} \
       BEGIN {printf \"%-40s %-20s %-20s\n\", \"====\", \"============\", \"===============\"} \
       {printf \"%-40s %-20s %-20s\n\", \$1, \$2, \$3}'"





