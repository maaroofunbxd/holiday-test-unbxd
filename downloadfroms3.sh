service="${1:-ner}"
mkdir -p ${service}-logs
aws s3 cp s3://unbxd-des/${service}loadtest/ ${service}-logs/ --recursive --exclude "*" --include "${service}-*.log"