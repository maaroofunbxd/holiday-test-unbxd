service="${1:-ner}"
mkdir -p ${service}-ap-southeast-1-logs
aws s3 cp s3://unbxd-des/${service}loadtest-ap-southeast-1/ ${service}-ap-southeast-1-logs/ --recursive --exclude "*" --include "${service}-*.log"