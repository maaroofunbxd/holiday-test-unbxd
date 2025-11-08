logfetchstart() {
    #CHECK if it is DEBUG or ERROR
    kubectl set env deployment/reranker --containers="pyreranker" LOG_LEVEL=DEBUG -nsearch
    kubectl set env deployment/reranker --containers="goreranker" LOG_LEVEL=debug -nsearch
    cd ~/mrf/holiday-test-unbxd/ ;
    sudo ./log-daemon.sh start app=reranker ./reranker-logs 
}


#steps
#1. upload logs to s3
sh uploadtos3.sh qcs

#2. download logs from s3
sh downloadfroms3.sh qcs

#3. process logs
sh ./process_logs.sh ner-logs ner ner

