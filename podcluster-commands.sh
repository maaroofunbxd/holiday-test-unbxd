./clustermonitor.sh qcs-demo 600 search
# kubectl get deploy qcs-demo -n ai -o yaml > demo.yaml
# kubectl get deploy qcs -n ai -o yaml > prod.yaml
# diff demo.yaml prod.yaml
#python3 commonpre-test.py
#git checkout AI-915
#helm upgrade qcs-demo  ./helm/qcs/ -f ./helm/qcs/values-aws-dev-ap-southeast-1.yaml -nai
bash