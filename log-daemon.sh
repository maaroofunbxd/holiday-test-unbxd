#!/bin/bash

# Daemon wrapper for monitor-logs.sh

# Usage function
usage() {
    echo "Usage: $0 {start|stop|restart|status|logs} <label-selector> <log-directory> [namespace] [check-interval] [size-threshold-mb]"
    echo ""
    echo "Commands:"
    echo "  start    - Start the monitor daemon"
    echo "  stop     - Stop the monitor daemon"
    echo "  restart  - Restart the monitor daemon"
    echo "  status   - Check if monitor is running"
    echo "  logs     - Show last 50 lines of monitor logs"
    echo "  logs -f  - Follow monitor logs in real-time"
    echo ""
    echo "Required Arguments (for start/restart):"
    echo "  label-selector     - Kubernetes label selector (e.g., app=reranker)"
    echo "  log-directory      - Directory to save logs (e.g., ./reranker-logs)"
    echo ""
    echo "Optional Arguments:"
    echo "  namespace          - Kubernetes namespace (default: search)"
    echo "  check-interval     - Check interval in seconds (default: 30)"
    echo "  size-threshold-mb  - Size threshold in MB to trigger save (default: 9.5)"
    echo ""
    echo "Example:"
    echo "  $0 start app=reranker ./reranker-logs"
    echo "  $0 start app=hodor ./hodor-logs search 30 9.5"
    echo "  $0 stop"
    echo "  $0 logs -f"
    exit 1
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MONITOR_SCRIPT="$SCRIPT_DIR/monitor-logs.sh"

# Function to generate PID and LOG file names based on label
get_filenames() {
    local label=$1
    # Sanitize label for filename (replace special chars with underscores)
    local safe_label=$(echo "$label" | sed 's/[^a-zA-Z0-9_-]/_/g')
    PID_FILE="$SCRIPT_DIR/${safe_label}-monitor.pid"
    LOG_FILE="$SCRIPT_DIR/${safe_label}-monitor.log"
}

# Function to start the daemon
start() {
    local label_selector="$1"
    local log_dir="$2"
    local namespace="${3:-search}"
    local check_interval="${4:-30}"
    local size_threshold="${5:-9.5}"
    
    if [ -z "$label_selector" ] || [ -z "$log_dir" ]; then
        echo "Error: label-selector and log-directory are required for start command"
        echo ""
        usage
    fi
    
    get_filenames "$label_selector"
    
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
    
    echo "Starting log monitor for '$label_selector'..."
    echo "Label: $label_selector"
    echo "Log directory: $log_dir"
    echo "Namespace: $namespace"
    
    # Export environment variables so nohup inherits them
    export AWS_PROFILE AWS_DEFAULT_REGION AWS_REGION AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN KUBECONFIG HOME PATH
    
    nohup "$MONITOR_SCRIPT" "$label_selector" "$log_dir" "$namespace" "$check_interval" "$size_threshold" >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    echo "Monitor started (PID: $PID)"
    echo "PID file: $PID_FILE"
    echo "Log file: $LOG_FILE"
    echo "To view logs: tail -f $LOG_FILE"
}

# Function to stop the daemon
stop() {
    local label_selector="$1"
    
    if [ -z "$label_selector" ]; then
        # If no label provided, try to find any running monitor
        local pid_files=("$SCRIPT_DIR"/*-monitor.pid)
        if [ ! -e "${pid_files[0]}" ]; then
            echo "No monitor PID files found"
            return 1
        fi
        
        echo "Found monitor PID files:"
        for pid_file in "${pid_files[@]}"; do
            if [ -f "$pid_file" ]; then
                local basename=$(basename "$pid_file" .pid)
                local label_name=$(echo "$basename" | sed 's/-monitor$//')
                echo "  - $label_name (PID file: $pid_file)"
            fi
        done
        echo ""
        echo "Please specify the label selector to stop:"
        echo "  $0 stop <label-selector>"
        return 1
    fi
    
    get_filenames "$label_selector"
    
    if [ ! -f "$PID_FILE" ]; then
        echo "Monitor for '$label_selector' is not running (no PID file found)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Stopping monitor for '$label_selector' (PID: $PID)..."
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
    local label_selector="$1"
    
    if [ -z "$label_selector" ]; then
        # If no label provided, show all running monitors
        local pid_files=("$SCRIPT_DIR"/*-monitor.pid)
        if [ ! -e "${pid_files[0]}" ]; then
            echo "No monitors are running"
            return 1
        fi
        
        echo "Running monitors:"
        local found=0
        for pid_file in "${pid_files[@]}"; do
            if [ -f "$pid_file" ]; then
                local pid=$(cat "$pid_file")
                if ps -p "$pid" > /dev/null 2>&1; then
                    local basename=$(basename "$pid_file" .pid)
                    local label_name=$(echo "$basename" | sed 's/-monitor$//')
                    echo "  - $label_name (PID: $pid)"
                    found=1
                fi
            fi
        done
        
        if [ $found -eq 0 ]; then
            echo "No monitors are running (found stale PID files)"
            return 1
        fi
        
        echo ""
        echo "For detailed status, specify the label selector:"
        echo "  $0 status <label-selector>"
        return 0
    fi
    
    get_filenames "$label_selector"
    
    if [ ! -f "$PID_FILE" ]; then
        echo "Monitor for '$label_selector' is not running"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "Monitor for '$label_selector' is running (PID: $PID)"
        echo "PID file: $PID_FILE"
        echo "Log file: $LOG_FILE"
        
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
    local label_selector="$1"
    local follow_flag="$2"
    
    if [ -z "$label_selector" ]; then
        # If no label provided, show available log files
        local log_files=("$SCRIPT_DIR"/*-monitor.log)
        if [ ! -e "${log_files[0]}" ]; then
            echo "No monitor log files found"
            return 1
        fi
        
        echo "Found monitor log files:"
        for log_file in "${log_files[@]}"; do
            if [ -f "$log_file" ]; then
                local basename=$(basename "$log_file" .log)
                local label_name=$(echo "$basename" | sed 's/-monitor$//')
                echo "  - $label_name (log: $log_file)"
            fi
        done
        echo ""
        echo "Please specify the label selector to view logs:"
        echo "  $0 logs <label-selector> [-f]"
        return 1
    fi
    
    get_filenames "$label_selector"
    
    if [ ! -f "$LOG_FILE" ]; then
        echo "No log file found for '$label_selector' at: $LOG_FILE"
        return 1
    fi
    
    if [ "$follow_flag" == "-f" ]; then
        tail -f "$LOG_FILE"
    else
        tail -50 "$LOG_FILE"
    fi
}

# Function to restart
restart() {
    local label_selector="$1"
    shift
    local args=("$@")
    
    if [ -z "$label_selector" ]; then
        echo "Error: label-selector is required for restart command"
        echo ""
        usage
    fi
    
    stop "$label_selector"
    sleep 2
    start "$label_selector" "${args[@]}"
}

# Main command handler
COMMAND="$1"
shift

case "$COMMAND" in
    start)
        start "$@"
        ;;
    stop)
        stop "$@"
        ;;
    restart)
        restart "$@"
        ;;
    status)
        status "$@"
        ;;
    logs)
        logs "$@"
        ;;
    *)
        usage
        ;;
esac

