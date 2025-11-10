service="${1:-ner}"
region="${2:-ap-southeast-1}"
mkdir -p ${service}-${region}-logs
aws s3 cp s3://unbxd-des/${service}loadtest-${region}/ ${service}-${region}-logs/ --recursive --exclude "*" --include "${service}-*.log"