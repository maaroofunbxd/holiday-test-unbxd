
# Change to the project directory

# Process all log files with given directory, prefix, service, and region
# Usage: ./process_logs.sh <directory> <prefix> <service> <region>
# Examples:
#   ./process_logs.sh reranker-ap-southeast-1-logs reranker reranker ap-southeast-1
#   ./process_logs.sh ner-ap-southeast-1-logs ner ner ap-southeast-1
#   ./process_logs.sh qcs-us-east-1-logs qcs qcs us-east-1
directory="${1:-reranker-ap-southeast-1-logs}"
prefix="${2:-reranker}"
service="${3:-reranker}"
region="${4:-ap-southeast-1}"

# Determine which extraction script to use based on service
case "$service" in
  reranker)
    extract_script="extract_requests.py"
    ;;
  ner)
    extract_script="extract_ner_requests.py"
    ;;
  qcs)
    extract_script="extract_qcs_requests.py"
    ;;
  *)
    extract_script="extract_requests.py"
    ;;
esac

find "$directory" -name "${prefix}-*.log" -type f | while read -r file; do
  basename_file=$(basename "$file" .log)
  output_file="${directory}/${service}_requests_${basename_file}.jsonl"
  python3 "$extract_script" -i "$file" -o "$output_file"
done
