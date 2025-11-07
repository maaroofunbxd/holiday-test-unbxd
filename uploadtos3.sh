service="${1:-ner}"
aws s3 cp ${service}-logs/. s3://unbxd-des/${service}loadtest/ --recursive --exclude "*" --include "${service}-*.log"

