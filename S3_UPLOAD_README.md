# S3 Auto-Upload Setup

## Overview
Scripts automatically queue output files and upload them to S3 using a centralized queue file approach.

## How It Works

### Queue File System (Simple!)
- Scripts write output file paths to a fixed file: `.s3_upload_queue` in their working directory
- No environment variables needed
- At the end of execution, the bash script reads all queue files and uploads files
- Queue files are automatically cleaned up after upload

### Architecture

```
┌─────────────────────────────────────────────────────┐
│  rerankerstart.sh                                   │
├─────────────────────────────────────────────────────┤
│  1. Clear any old queue file                        │
│     rm -f .s3_upload_queue                         │
│                                                     │
│  2. Run BOTH Python monitors in PARALLEL           │
│     ├─> Script #1 (reranker-demo) &               │
│     │   └─> Writes to .s3_upload_queue            │
│     └─> Script #2 (ranking/embedding) &           │
│         └─> Writes to .s3_upload_queue            │
│     wait for both to complete                      │
│                                                     │
│  3. Run k6 script                                  │
│     └─> Appends paths to .s3_upload_queue          │
│                                                     │
│  4. Read .s3_upload_queue and upload to S3        │
│     └─> aws s3 cp each file                        │
│                                                     │
│  5. Clean up queue file                            │
│     rm -f .s3_upload_queue                         │
└─────────────────────────────────────────────────────┘
```

## Modified Files

### 1. `monitor-pod-resources.py`
**Changes:**
- Writes absolute paths of all output files to `.s3_upload_queue`
- Simple, no environment variables needed
- Handles errors gracefully if queue file is not writable

**Output files added to queue:**
- `{timestamp}test.csv`
- `{timestamp}test_summary.txt`
- `{timestamp}test_events.csv` (if lifecycle events exist)

### 2. `rerankerstart.sh`
**Changes:**
- Clears any existing `.s3_upload_queue` at start
- After k6 runs, bash appends output paths to `.s3_upload_queue`
- At the end, reads queue files from both directories and uploads all files to S3
- Cleans up queue files after upload

**Bash section at end:**
```bash
# Collect all queue files from both directories
QUEUE_FILES=(
    ~/mrf/holiday-test-unbxd/.s3_upload_queue
    ~/mrf/loadtest/holiday-test-unbxd/.s3_upload_queue
)

for queue_file in "${QUEUE_FILES[@]}"; do
    if [ -f "$queue_file" ]; then
        while IFS= read -r file_path; do
            aws s3 cp "$file_path" s3://unbxd-des/rerankerloadtest/
        done < "$queue_file"
        rm -f "$queue_file"
    fi
done
```

### 3. `run-reranker-load.sh`
**Changes:**
- Standalone script with same queue-based approach
- Uses `.s3_upload_queue` in current directory
- Captures k6 output and summary
- Uploads all files to S3 at the end

## Queue File Format

### `.s3_upload_queue`
- **Location:** Current working directory where script runs
- **Format:** One absolute file path per line
- **Created by:** Python scripts and bash scripts
- **Read by:** Bash scripts at the end
- **Cleaned up:** Automatically deleted after upload

**Example content:**
```
/home/user/mrf/holiday-test-unbxd/20251105-1449test.csv
/home/user/mrf/holiday-test-unbxd/20251105-1449test_summary.txt
/home/user/mrf/loadtest/holiday-test-unbxd/20251105-1449raw-data.json
```

## Usage

### Run Complete Test Suite
```bash
bash rerankerstart.sh
```

This will:
1. Clear any old queue files
2. Run **TWO** `monitor-pod-resources.py` scripts **in parallel** (simultaneously)
   - Both monitoring reranker-demo and ranking/embedding pods at the same time
   - Both write to `.s3_upload_queue`
3. Wait for both monitors to complete
4. Run k6 load test → appends to `.s3_upload_queue`
5. Upload all queued files to S3
6. Clean up queue files

### Skip S3 Upload (for testing)
```bash
SKIP_S3_UPLOAD=true bash rerankerstart.sh
```

### Change S3 Bucket
Edit the `S3_BUCKET` variable in the script:
```bash
S3_BUCKET="s3://your-bucket/your-path/"
```

### Run Standalone K6 Test
```bash
bash run-reranker-load.sh
```

This will:
1. Clear any old queue file
2. Run k6 test and capture output
3. Add output files to `.s3_upload_queue`
4. Upload all files to S3
5. Clean up queue file

## Output Files

All files are uploaded to: `s3://unbxd-des/rerankerloadtest/`

### From monitor-pod-resources.py:
**First run (reranker-demo):**
- `20251105-1449reranker-demo.csv` - Container metrics
- `20251105-1449reranker-demo_summary.txt` - Summary statistics
- `20251105-1449reranker-demo_events.csv` - Lifecycle events (if any)

**Second run (ranking/embedding):**
- `20251105-1449ranking-embedding.csv` - Container metrics
- `20251105-1449ranking-embedding_summary.txt` - Summary statistics
- `20251105-1449ranking-embedding_events.csv` - Lifecycle events (if any)

### From k6 load tests:
- `20251105-1449raw-data.json` - Raw k6 data
- `20251105-1449summary.json` - k6 summary
- `20251105-1449reranker-load-test.txt` - Full k6 output
- `20251105-1449reranker-load-test_summary.txt` - Last 30 lines

## Benefits of Queue Approach

1. **Simple:** No environment variables, just a fixed file name
2. **Decoupling:** Scripts don't need to know about S3 or AWS CLI
3. **Flexibility:** Easy to add more output files to queue
4. **Error Handling:** Detailed tracking of uploaded/failed/missing files
5. **Debugging:** Queue file shows exactly what will be uploaded
6. **Configurable:** Can skip uploads, change S3 bucket easily
7. **Single Responsibility:** 
   - Python/JS scripts: Generate outputs and list them in queue
   - Bash script: Handle S3 uploads

## Refactored Upload Features

### Configuration
- **S3_BUCKET**: Centralized bucket configuration at top of script
- **SKIP_S3_UPLOAD**: Environment variable to skip uploads for testing

### Improved Upload Function
- **Modular**: `upload_from_queue()` function for clean code
- **Better Tracking**: Counts uploaded, failed, and missing files separately
- **Cleaner Output**: Emojis and summary statistics per queue
- **Error Suppression**: `--only-show-errors` flag for cleaner AWS output
- **Safer**: Validates file existence before upload attempt

### Example Output
```
📤 Uploading to S3: s3://unbxd-des/rerankerloadtest/
📁 Processing: holiday-test-unbxd/.s3_upload_queue
  ✅ 20251105-1449reranker-demo.csv
  ✅ 20251105-1449reranker-demo_summary.txt
  ⚠️  Not found: 20251105-1449reranker-demo_events.csv
  └─ Uploaded: 2 | Failed: 0 | Missing: 1
📁 Processing: holiday-test-unbxd/.s3_upload_queue
  ✅ 20251105-1449raw-data.json
  ✅ 20251105-1449summary.json
  └─ Uploaded: 2 | Failed: 0 | Missing: 0
=========================================
✅ Total files uploaded: 4
=========================================
```

## Error Handling

### Python Script
- If queue file can't be written, shows warning but continues
- Files are still saved locally even if queue fails

### Bash Script
- Checks if each file exists before uploading
- Shows status for each upload (✓ success, ✗ failed, ⚠ not found)
- Continues uploading remaining files if one fails

## Troubleshooting

### Queue file not found
- Queue file is `.s3_upload_queue` in the working directory
- Make sure scripts have write permissions in their directories

### Files not uploading
- Check AWS credentials: `aws sts get-caller-identity`
- Check S3 bucket access: `aws s3 ls s3://unbxd-des/rerankerloadtest/`
- Check if files exist at the paths in queue file
- Look at the queue file contents: `cat .s3_upload_queue`

### Python script not adding files to queue
- Look for warning messages in Python output
- Check file permissions on current directory
- Verify script completed successfully

## Requirements
- AWS CLI configured with appropriate credentials
- Access to `s3://unbxd-des/rerankerloadtest/`
- Python 3 with pandas and tabulate
- k6 or Docker with grafana/k6 image
- Bash 4.0 or later

## Clean Up

Queue files are automatically removed after upload. If a script fails before cleanup:
```bash
# From the directory where script ran
rm -f .s3_upload_queue
```

