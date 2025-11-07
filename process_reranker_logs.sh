
# Change to the project directory

# Process all log files with given prefix and directory
# Usage: ./process_reranker_logs.sh <directory> <prefix>
directory="${1:-reranker-logs}"
prefix="${2:-reranker}"

find "$directory" -name "${prefix}-*.log" -type f | while read -r file; do
  basename_file=$(basename "$file" .log)
  output_file="${directory}/requests_${basename_file}.jsonl"
  python3 extract_requests.py -i "$file" -o "$output_file"
done

# AWS S3 commands (commented out)
# aws s3 ls s3://unbxd-des/rerankerloadtest/

# aws s3 cp . s3://unbxd-des/rerankerloadtest/gcpuslogs/ --recursive --exclude "*" --include "*.jsonl"

# aws s3 cp s3://unbxd-des/rerankerloadtest/gcpuslogs/ . --recursive --exclude "*" --include "*.jsonl"

