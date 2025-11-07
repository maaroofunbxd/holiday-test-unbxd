mkdir -p ner-logs
aws s3 cp s3://unbxd-des/nerloadtest/ ner-logs/ --recursive --exclude "*" --include "ner-*"