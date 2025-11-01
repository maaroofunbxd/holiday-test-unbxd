#!/bin/bash
#kubectl set env deployment/reranker-demo --containers="pyreranker" LOG_LEVEL=DEBUG
#kubectl set env deployment/reranker-demo --containers="goreranker" LOG_LEVEL=debug
# Configuration
NAMESPACE="search"
LABEL_SELECTOR="app=reranker"
CHECK_INTERVAL=30  # Check every 30 seconds
SIZE_THRESHOLD_MB=9.5  # Save when logs reach 9.5MB (before 10MB rotation)
LOG_DIR="./reranker-logs"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create log directory
mkdir -p "$LOG_DIR"

echo "Starting log monitor for app=reranker pods in namespace: $NAMESPACE"
echo "Logs will be saved to: $LOG_DIR"
echo "Check interval: ${CHECK_INTERVAL}s"
echo "Size threshold: ${SIZE_THRESHOLD_MB}MB"
echo "---"

# Track last known sizes
declare -A last_sizes

# Function to get timestamp for filename
get_timestamp() {
    date '+%Y%m%d_%H%M%S'
}

# Function to get human-readable timestamp
get_human_time() {
    date '+%Y-%m-%d %H:%M:%S'
}

# Function to check and save logs for a pod/container
check_pod_logs() {
    local pod=$1
    local container=$2
    local key="${pod}_${container}"
    
    # Get current log size
    size_bytes=$(kubectl logs "$pod" -n "$NAMESPACE" -c "$container" 2>/dev/null | wc -c | tr -d ' ')
    
    if [ -z "$size_bytes" ] || [ "$size_bytes" -eq 0 ]; then
        return
    fi
    
    # Convert to MB
    size_mb=$(echo "scale=2; $size_bytes / 1024 / 1024" | bc)
    
    # Check if size dropped (rotation occurred)
    if [ -n "${last_sizes[$key]}" ]; then
        last_size="${last_sizes[$key]}"
        if [ "$size_bytes" -lt "$last_size" ]; then
            echo -e "${RED}[$(get_human_time)]${NC} ⚠️  ROTATION DETECTED: $pod/$container"
            echo "  Size dropped: $(echo "scale=2; $last_size / 1024 / 1024" | bc)MB -> ${size_mb}MB"
        fi
    fi
    
    # Check if approaching threshold
    threshold_check=$(echo "$size_mb >= $SIZE_THRESHOLD_MB" | bc -l)
    if [ "$threshold_check" -eq 1 ]; then
        timestamp=$(get_timestamp)
        filename="${LOG_DIR}/${pod}_${container}_${timestamp}.log"
        
        echo -e "${YELLOW}[$(get_human_time)]${NC} 📝 Saving logs: $pod/$container (${size_mb}MB)"
        
        # Save logs with timestamps
        kubectl logs "$pod" -n "$NAMESPACE" -c "$container" --timestamps > "$filename" 2>/dev/null
        
        if [ $? -eq 0 ]; then
            file_size=$(ls -lh "$filename" | awk '{print $5}')
            echo -e "${GREEN}[$(get_human_time)]${NC} ✓ Saved: $(basename $filename) ($file_size)"
            
            # Get log metadata
            oldest_log=$(head -1 "$filename" | awk '{print $1}')
            newest_log=$(tail -1 "$filename" | awk '{print $1}')
            line_count=$(wc -l < "$filename" | tr -d ' ')
            
            echo "  Time range: $oldest_log to $newest_log"
            echo "  Lines: $line_count"
            
            # Reset tracking to avoid repeated saves
            last_sizes[$key]=0
        else
            echo -e "${RED}[$(get_human_time)]${NC} ✗ Failed to save logs for $pod/$container"
        fi
    else
        # Normal monitoring output (less verbose)
        echo "[$(get_human_time)] $pod/$container: ${size_mb}MB"
    fi
    
    # Update last known size
    last_sizes[$key]=$size_bytes
}

# Main monitoring loop
while true; do
    # Get all pods matching the label selector
    pods=$(kubectl get pods -n "$NAMESPACE" -l "$LABEL_SELECTOR" -o jsonpath='{.items[*].metadata.name}' 2>/dev/null)
    
    if [ -z "$pods" ]; then
        echo -e "${RED}[$(get_human_time)]${NC} No pods found with label $LABEL_SELECTOR in namespace $NAMESPACE"
        sleep "$CHECK_INTERVAL"
        continue
    fi
    
    # Process each pod
    for pod in $pods; do
        # Get container names for this pod
        containers=$(kubectl get pod "$pod" -n "$NAMESPACE" -o jsonpath='{.spec.containers[*].name}' 2>/dev/null)
        
        if [ -z "$containers" ]; then
            continue
        fi
        
        # Check logs for each container
        for container in $containers; do
            check_pod_logs "$pod" "$container"
        done
    done
    
    echo "---"
    sleep "$CHECK_INTERVAL"
done

