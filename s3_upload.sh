cleanup() {
    echo ""
    echo "🛑 Interrupt received, cleaning up..."
    
    # Kill monitor processes if they're still running
    if [ ! -z "$MONITOR_PID1" ] && kill -0 $MONITOR_PID1 2>/dev/null; then
        echo "  Stopping monitor 1 (PID: $MONITOR_PID1)..."
        kill $MONITOR_PID1 2>/dev/null
    fi
    
    if [ ! -z "$MONITOR_PID2" ] && kill -0 $MONITOR_PID2 2>/dev/null; then
        echo "  Stopping monitor 2 (PID: $MONITOR_PID2)..."
        kill $MONITOR_PID2 2>/dev/null
    fi
    
    echo "✓ Cleanup complete"
    exit 130
}


# ========================================
# S3 Upload Module
# ========================================

# Configuration
S3_BUCKET="s3://unbxd-des/rerankerloadtest/"
SKIP_S3_UPLOAD="${SKIP_S3_UPLOAD:-false}"
AWS_OPTS="--only-show-errors"

# Get queue file display name
get_queue_display_name() {
    local queue_file="$1"
    echo "$(basename $(dirname $queue_file))/$(basename $queue_file)"
}

# Check if file exists and is valid
validate_file() {
    local file_path="$1"
    [ -n "$file_path" ] && [ -f "$file_path" ]
}

# Upload single file to S3
upload_file_to_s3() {
    local file_path="$1"
    local filename=$(basename "$file_path")
    
    if ! validate_file "$file_path"; then
        echo "  ⚠️  Not found: $filename"
        return 2  # Missing
    fi
    
    if aws s3 cp "$file_path" "$S3_BUCKET" $AWS_OPTS 2>&1; then
        # Show full S3 path instead of just filename
        local s3_path="${S3_BUCKET}${filename}"
        echo "  ✅ ${s3_path}"
        return 0  # Success
    else
        echo "  ❌ Failed: $filename"
        return 1  # Failed
    fi
}

# Display upload statistics
display_stats() {
    local uploaded=$1
    local failed=$2
    local missing=$3
    echo "  └─ Uploaded: $uploaded | Failed: $failed | Missing: $missing"
}

# Process single queue file
process_queue_file() {
    local queue_file="$1"
    local uploaded=0
    local failed=0
    local missing=0
    
    [ ! -f "$queue_file" ] && return 0
    
    echo "📁 Processing: $(get_queue_display_name "$queue_file")"
    
    while IFS= read -r file_path; do
        # Skip empty lines
        [ -z "$file_path" ] && continue
        
        upload_file_to_s3 "$file_path"
        case $? in
            0) ((uploaded++)) ;;
            1) ((failed++)) ;;
            2) ((missing++)) ;;
        esac
    done < "$queue_file"
    
    display_stats $uploaded $failed $missing
    
    # Clean up queue file
    rm -f "$queue_file"
    
    return $uploaded
}

# Main upload orchestrator
# Usage: run_s3_upload queue_file1 [queue_file2 ...]
run_s3_upload() {
    [ "$SKIP_S3_UPLOAD" = "true" ] && {
        echo ""
        echo "⏭️  Skipping S3 upload (SKIP_S3_UPLOAD=true)"
        echo ""
        return 0
    }
    
    [ $# -eq 0 ] && {
        echo "⚠️  No queue files specified"
        return 1
    }
    
    echo ""
    echo "========================================="
    echo "📤 Uploading to S3: $S3_BUCKET"
    echo "========================================="
    
    local total_uploaded=0
    
    for queue_file in "$@"; do
        process_queue_file "$queue_file"
        total_uploaded=$((total_uploaded + $?))
    done
    
    echo "========================================="
    if [ $total_uploaded -gt 0 ]; then
        echo "✅ Total files uploaded: $total_uploaded"
    else
        echo "⚠️  No files were uploaded"
    fi
    echo "========================================="
    echo ""
}


