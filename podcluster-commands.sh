#./clustermonitor.sh qcs-demo 600 search
kubectl get deploy qcs-demo -n search -o yaml > demo.yaml
kubectl get deploy qcs -n search -o yaml > prod.yaml
diff demo.yaml prod.yaml
bash
#python3 commonpre-test.py