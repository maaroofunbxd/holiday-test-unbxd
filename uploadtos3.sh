service="${1:-ner}"
aws s3 cp ${service}-logs/. s3://unbxd-des/${service}loadtest-ap-southeast-1/ --recursive --exclude "*" --include "${service}-*.log"

