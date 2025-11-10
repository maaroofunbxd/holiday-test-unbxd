#!/bin/bash

# Simple background log monitor - no tmux/screen needed
# Usage: ./simple-log-monitor.sh {start|stop|status|list|tail} [label-selector] [log-directory]

ACTION="$1"
LABEL_SELECTOR="${2:-app=reranker}"
LOG_DIR="${3:-./reranker-logs}"
NAMESPACE="${4:-search}"
CHECK_INTERVAL="${5:-30}"
SIZE_THRESHOLD="${6:-9.5}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SAFE_LABEL=$(echo "$LABEL_SELECTOR" | sed 's/[^a-zA-Z0-9_-]/_/g')
PID_FILE="$SCRIPT_DIR/${SAFE_LABEL}.pid"
MONITOR_LOG="$SCRIPT_DIR/${SAFE_LABEL}-monitor.log"

start_monitor() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Monitor already running (PID: $PID)"
            return 1
        fi
        rm -f "$PID_FILE"
    fi
    
    mkdir -p "$LOG_DIR"
    
    # Create log and PID files with proper permissions
    touch "$MONITOR_LOG" 2>/dev/null || { echo "Error: Cannot create $MONITOR_LOG"; return 1; }
    touch "$PID_FILE" 2>/dev/null || { echo "Error: Cannot create $PID_FILE"; return 1; }
    chmod 644 "$MONITOR_LOG" "$PID_FILE" 2>/dev/null
    
    echo "Starting monitor for '$LABEL_SELECTOR'..."
    echo "Saving pod logs to: $LOG_DIR/"
    echo "Monitor output: $MONITOR_LOG"
    
    # Run monitor in background, redirect output to log file
    ./monitor-logs.sh "$LABEL_SELECTOR" "$LOG_DIR" "$NAMESPACE" "$CHECK_INTERVAL" "$SIZE_THRESHOLD" > "$MONITOR_LOG" 2>&1 &
    
    echo $! > "$PID_FILE"
    echo "Started (PID: $!)"
}

stop_monitor() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Monitor not running (no PID file)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping monitor (PID: $PID)..."
        kill "$PID"
        sleep 1
        [ -f "$PID_FILE" ] && rm -f "$PID_FILE"
        echo "Stopped."
    else
        echo "Monitor not running (stale PID)"
        rm -f "$PID_FILE"
    fi
}

status_monitor() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✓ Monitor is running (PID: $PID)"
            echo "  Label: $LABEL_SELECTOR"
            echo "  Log directory: $LOG_DIR"
            echo "  Monitor log: $MONITOR_LOG"
            echo ""
            echo "Recent activity:"
            tail -5 "$MONITOR_LOG" 2>/dev/null || echo "  (no logs yet)"
            return 0
        fi
    fi
    echo "✗ Monitor is not running"
    return 1
}

list_logs() {
    if [ ! -d "$LOG_DIR" ]; then
        echo "No logs directory found: $LOG_DIR"
        return 1
    fi
    
    echo "Saved pod logs in $LOG_DIR:"
    ls -lht "$LOG_DIR"/*.log 2>/dev/null | head -20 || echo "  (no logs saved yet)"
}

tail_logs() {
    echo "Monitor output (last 50 lines):"
    echo "================================"
    tail -50 "$MONITOR_LOG" 2>/dev/null || echo "(no monitor log yet)"
    echo ""
    echo "To follow: tail -f $MONITOR_LOG"
}

case "$ACTION" in
    start)
        start_monitor
        ;;
    stop)
        stop_monitor
        ;;
    status)
        status_monitor
        ;;
    list)
        list_logs
        ;;
    tail|logs)
        tail_logs
        ;;
    *)
        echo "Usage: $0 {start|stop|status|list|tail} [label-selector] [log-directory] [namespace] [interval] [threshold]"
        echo ""
        echo "Commands:"
        echo "  start  - Start monitoring in background"
        echo "  stop   - Stop monitoring"
        echo "  status - Check if running"
        echo "  list   - List saved pod log files"
        echo "  tail   - Show monitor output"
        echo ""
        echo "Examples:"
        echo "  $0 start                              # Start with defaults"
        echo "  $0 start app=reranker ./reranker-logs # Start with custom settings"
        echo "  $0 status                             # Check if running"
        echo "  $0 list                               # List saved log files"
        echo "  $0 tail                               # See what monitor is doing"
        exit 1
        ;;
esac

