#sudo chown -R $USER:$USER .
#./simple-log-monitor.sh start app=qcs ./qcs-gcp-us-logs
#sh ./pre-test-qcs.sh
#python3 commonpre-test.py
#kubectl get deploy qcs-demo -n ai -o yaml > demo.yaml
#kubectl get deploy qcs -n ai -o yaml > prod.yaml
#diff demo.yaml prod.yaml
#python3 commonpre-test.py
#git checkout AI-915
#helm upgrade qcs-demo ./helm/qcs/ -f ./helm/qcs/values-aws-dev-ap-southeast-1.yaml -nai

pip3 install pandas tabulate
./clustermonitor.sh qcs-demo 600 ai
pip3 uninstall pandas tabulate