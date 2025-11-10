logfetchstart() {
    #CHECK if it is DEBUG or ERROR
    kubectl set env deployment/reranker --containers="pyreranker" LOG_LEVEL=DEBUG -nsearch
    kubectl set env deployment/reranker --containers="goreranker" LOG_LEVEL=debug -nsearch
    cd ~/mrf/holiday-test-unbxd/ ;
    # Simple background monitor - no sudo/tmux/screen needed!
    ./simple-log-monitor.sh start app=reranker ./reranker-logs search 30 6
}

logfetchstop() {
    cd ~/mrf/holiday-test-unbxd/ ;
    ./simple-log-monitor.sh stop
}

logfetchstatus() {
    cd ~/mrf/holiday-test-unbxd/ ;
    ./simple-log-monitor.sh status
}

logfetchlist() {
    cd ~/mrf/holiday-test-unbxd/ ;
    ./simple-log-monitor.sh list
}

logfetchview() {
    # View what the monitor is doing
    cd ~/mrf/holiday-test-unbxd/ ;
    ./simple-log-monitor.sh tail
}


aws s3 cp  qcs-use-1d-logs/ s3://unbxd-des/qcsloadtest-use-1d/ --recursive --exclude "*" --include "qcs_*.jsonl"
aws s3 cp  ner-use-1d-logs/ s3://unbxd-des/nerloadtest-use-1d/ --recursive --exclude "*" --include "ner_*.jsonl"
aws s3 cp s3://unbxd-des/rerankerloadtest-use-1d/ reranker-use-1d-logs/ --recursive --exclude "*" --include "reranker-*.log"
#steps
#1. from cluster,upload logs to s3
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "'sh uploadtos3.sh reranker'"
sh uploadtos3.sh reranker

#2. ubuntu serverdownload logs from s3
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh downloadfroms3.sh qcs'"
sh downloadfroms3.sh ner use-1d

#3. ubuntu server, process logs
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accessloadtestcluster.sh "'sh ./process_logs.sh reranker-ap-southeast-1-logs reranker reranker'"
sh ./process_logs.sh ner-logs ner ner
rm reranker-ap-southeast-1-logs/*.log
