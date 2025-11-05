# kubectl set env deploy/reranker-demo -nsearch --list
# kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_CACHE_TTL=80
# aws s3 ls s3://unbxd-des/rerankerloadtest/
# aws s3 cp s3://unbxd-des/rerankerloadtest/ . --recursive --exclude "*" --include "*.jsonl"
# watch -n 5 kubectl top pods -l algo=personalization
# kubectl top pods -l'algo in (personalization,ranking)' --no-headers

#run from ai-prod-us-east-1-eks@ip-10-0-40-71
time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)
cd holiday-test-unbxd; python3 monitor-pod-resources.py --stats 80 --watch 5  -l "app in (reranker-demo)" --output ${time_ist}test.csv; cd ..


#run from ubuntu@ip-10-0-1-231
cd mrf; cd holiday-test-unbxd/;  
FILES=$(find "$(pwd)/reranker-logs" -maxdepth 1 -name "*.jsonl" -type f | tr '\n' ',' | sed 's/,$//')
time_ist=$(TZ=Asia/Kolkata date +%Y%m%d-%H%M)
k6 run -e RPS=40 -e DURATION=60s -e HOST=http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com -e INPUT_FILES="$FILES" --out json=${time_ist}raw-data.json --summary-export=${time_ist}summary.json reranker-load-test.js ; 
cd ..


