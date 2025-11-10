service="${1:-ner}"
region="${2:-ap-southeast-1}"
aws s3 cp ${service}-${region}-logs/. s3://unbxd-des/${service}loadtest-${region}/ --recursive --exclude "*" --include "${service}-*.log"

