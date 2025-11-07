# AWS S3 commands (commented out)
#aws s3 ls s3://unbxd-des/rerankerloadtest/

aws s3 cp ner-logs/. s3://unbxd-des/nerloadtest/ --recursive --exclude "*" --include "ner-*"

