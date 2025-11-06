
# Change to the project directory
cd 'holiday-test-unbxd/'

# Monitor reranker logs (commented out)
#./monitor-reranker-logs.sh

# Start the reranker log daemon with sudo
sudo './reranker-log-daemon.sh' 'start'

# Process all reranker log files
# find 'reranker-logs' '-name' 'reranker-*.log' '-type' 'f' >>= foreach
#   str file = echo argv[1]
#   str basename_file = basename file '.log'
#   str output_file = echo 'reranker-logs/requests_' basename_file '.jsonl'
#   python3 'extract_requests.py' '-i' file '-o' output_file

# AWS S3 commands (commented out)
# aws s3 ls s3://unbxd-des/rerankerloadtest/

# aws s3 cp . s3://unbxd-des/rerankerloadtest/gcpuslogs/ --recursive --exclude "*" --include "*.jsonl"

# aws s3 cp s3://unbxd-des/rerankerloadtest/gcpuslogs/ . --recursive --exclude "*" --include "*.jsonl"

