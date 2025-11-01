#!/bin/bash

# Daemon wrapper for monitor-reranker-logs.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/monitor-reranker-logs.sh"
PID_FILE="$SCRIPT_DIR/reranker-monitor.pid"
LOG_FILE="$SCRIPT_DIR/reranker-monitor.log"

# Function to start the daemon
start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Monitor is already running (PID: $PID)"
            return 1
        else
            echo "Removing stale PID file"
            rm -f "$PID_FILE"
        fi
    fi
    
    echo "Starting reranker log monitor..."
    nohup "$MONITOR_SCRIPT" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    echo "Monitor started (PID: $PID)"
    echo "Log file: $LOG_FILE"
    echo "To view logs: tail -f $LOG_FILE"
}

# Function to stop the daemon
stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Monitor is not running (no PID file found)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping monitor (PID: $PID)..."
        kill "$PID"
        
        # Wait for process to stop
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "Process didn't stop gracefully, forcing..."
            kill -9 "$PID"
        fi
        
        rm -f "$PID_FILE"
        echo "Monitor stopped"
    else
        echo "Monitor is not running (stale PID file)"
        rm -f "$PID_FILE"
    fi
}

# Function to check status
status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Monitor is not running"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Monitor is running (PID: $PID)"
        echo "Log file: $LOG_FILE"
        echo "Saved logs directory: $SCRIPT_DIR/reranker-logs/"
        
        # Show recent activity
        if [ -f "$LOG_FILE" ]; then
            echo ""
            echo "Last 5 log entries:"
            tail -5 "$LOG_FILE"
        fi
    else
        echo "Monitor is not running (stale PID file)"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to show logs
logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "No log file found at: $LOG_FILE"
        return 1
    fi
    
    if [ "$1" == "-f" ]; then
        tail -f "$LOG_FILE"
    else
        tail -50 "$LOG_FILE"
    fi
}

# Function to restart
restart() {
    stop
    sleep 2
    start
}

# Main command handler
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "${2:-}"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs [-f]}"
        echo ""
        echo "Commands:"
        echo "  start    - Start the monitor daemon"
        echo "  stop     - Stop the monitor daemon"
        echo "  restart  - Restart the monitor daemon"
        echo "  status   - Check if monitor is running"
        echo "  logs     - Show last 50 lines of monitor logs"
        echo "  logs -f  - Follow monitor logs in real-time"
        exit 1
        ;;
esac

