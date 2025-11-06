# last years (2024) reranker go use-1d showing much larger RPS for use-1d than now : max -> (20,0.1)
# reranker2024:
#     go:
#         rps:
#             max: 20
            
# https://docs.google.com/spreadsheets/d/1HwN-W9mj1CcGNLGZNTpzbyFk-dG8ZJoOBkCnn54sWy8/edit?gid=0#gid=0
# https://app.datadoghq.com/dashboard/dbd-x57-fig/reranker?fromUser=true&fullscreen_end_ts=1762159766854&fullscreen_paused=false&fullscreen_refresh_mode=sliding&fullscreen_section=overview&fullscreen_start_ts=1761554966854&fullscreen_widget=8411901009295312&refresh_mode=sliding&tpl_var_region%5B0%5D=us-east-1&from_ts=1762073314258&to_ts=1762159714258&live=true


kubectl get configmap  reranker-envoy -nsearch -oyaml > prodenvoyconfigmap.yaml
kubectl get configmap  reranker-demo-envoy -nsearch -oyaml > olddemoconfigmap.yaml
kubectl get configmap reranker-envoy -nsearch -o json | jq '{data: .data}' > tmp.json
kubectl patch configmap reranker-demo-envoy -nsearch --type merge -p "$(cat tmp.json)"
#edit it manually if needed
#kubectl delete configmap reranker-demo-envoy
# cat > democonfigmap.yaml <<EOF
# EOF
#kubectl apply -f democonfigmap.yaml


kubectl get deploy reranker-demo -nsearch -oyaml > demo.yaml
kubectl get deploy reranker -nsearch -oyaml > prod.yaml
#in local
dyff between demo.yaml prod.yaml

SOURCE_IMAGE=$(kubectl get deployment reranker -nsearch -o jsonpath="{.spec.template.spec.containers[?(@.name=='pyreranker')].image}")
echo "SOURCE_IMAGE: $SOURCE_IMAGE"
CURRENT_IMAGE=$(kubectl get deployment reranker-demo -nsearch -o jsonpath="{.spec.template.spec.containers[?(@.name=='pyreranker')].image}")
echo "CURRENT_IMAGE: $CURRENT_IMAGE"
kubectl set image deployment/reranker-demo -nsearch pyreranker=$SOURCE_IMAGE

SOURCE_IMAGE=$(kubectl get deployment reranker -nsearch -o jsonpath="{.spec.template.spec.containers[?(@.name=='goreranker')].image}")
echo "SOURCE_IMAGE: $SOURCE_IMAGE"
CURRENT_IMAGE=$(kubectl get deployment reranker-demo -nsearch -o jsonpath="{.spec.template.spec.containers[?(@.name=='goreranker')].image}")
echo "CURRENT_IMAGE: $CURRENT_IMAGE"
kubectl set image deployment/reranker-demo -nsearch goreranker=$SOURCE_IMAGE


POLICY=$(kubectl get deploy reranker -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].imagePullPolicy}')
kubectl patch deploy reranker-demo -nsearch -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"goreranker\",\"imagePullPolicy\":\"$POLICY\"}]}}}}"
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].imagePullPolicy}'

POLICY=$(kubectl get deploy reranker -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="pyreranker")].imagePullPolicy}')
kubectl patch deploy reranker-demo -nsearch -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"pyreranker\",\"imagePullPolicy\":\"$POLICY\"}]}}}}"
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="pyreranker")].imagePullPolicy}'



# 1️⃣ Extract container config from source
CONTAINER=$(kubectl get deploy reranker -nsearch -o json | jq -c '.spec.template.spec.containers[] | select(.name=="goreranker") | {name,resources,livenessProbe,readinessProbe}')

# 2️⃣ Print existing target container values before patching
echo "---- Current target values ----"
kubectl get deploy reranker-demo -nsearch -o json | jq '.spec.template.spec.containers[] | select(.name=="goreranker") | {name,resources,livenessProbe,readinessProbe}'

# 3️⃣ Patch the target with the copied specs
kubectl patch deploy reranker-demo -nsearch -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[${CONTAINER}]}}}}"

# 4️⃣ Confirm new values
echo "---- Updated target values ----"
kubectl get deploy reranker-demo -o json | jq '.spec.template.spec.containers[] | select(.name=="goreranker") | {name,resources,livenessProbe,readinessProbe}'

kubectl patch deploy reranker-demo -nsearch -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"goreranker\",$SPECS}]}}}}"
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].livenessProbe}'
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].readinessProbe}'
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].resources}'


#gcp us
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" DATASTORE_CONN_TIMEOUT=1000
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" LOG_LEVEL=error

kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" IS_PIPELINES_IFSVC_TIMEOUT=5 
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" MIMIR_HOST='http://mimir.pilot-rc-unbxd.infra'

kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" VISION_IMAGE_LOCATION=us-east1
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" VISION_TIMEOUT=10000


kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" AE_TIMEOUT=5000
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ASTERIX_ENDPOINT='http://asterix.pilot-rc-unbxd.infra'

kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" PIPELINES_IFSVC_TIMEOUT=0.5
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" LOG_LEVEL=ERROR
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_CONNECT_TIMEOUT=100
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_CONNECT_TIMEOUT_RERANKER=0.05
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_TIMEOUT=100
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_TIMEOUT_RERANKER=0.1
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REGION=us-east-4
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" SEMANTIC_CACHE_SCORE_THRESHOLD=0.95
statsd_host=statsd.pilot-rc-unbxd.infra
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" STATSD_HOST=$statsd_host

kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" OLYMPUS_TIMEOUT=0.05
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" OLYMPUS_CONNECT_TIMEOUT=0.05

kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" NETCORE_EVENTS_SET=nc_user_data

replicas=$(kubectl get deploy reranker -nsearch -o jsonpath='{.spec.replicas}')
kubectl scale deploy reranker-demo -nsearch --replicas="$replicas"

kubectl annotate deploy reranker-demo -n search \
  kubernetes.io/change-cause="increased replicas to $replicas"


kubectl rollout restart deployment reranker-demo -nsearch
kubectl rollout status deployment reranker-demo -nsearch
kubectl rollout history deployment reranker-demo -nsearch
# kubectl rollout undo deployment reranker-demo -nsearch
# kubectl rollout undo deployment reranker-demo -nsearch --to-revision=1

#TO GET the prod logs
kubectl set env deployment/reranker -nsearch --containers="goreranker" LOG_LEVEL=debug
kubectl annotate deploy reranker -n search \
  kubernetes.io/change-cause="goreranker debugging"

kubectl set env deployment/reranker -nsearch --containers="pyreranker" LOG_LEVEL=DEBUG
kubectl annotate deploy reranker -n search \
  kubernetes.io/change-cause="pyreranker debugging"
kubectl rollout status deployment reranker -nsearch
kubectl rollout history deployment reranker -nsearch

#kubectl set env deploy/reranker-demo -nsearch --list
kubectl set env deployment/reranker --containers="pyreranker" LOG_LEVEL=ERROR -nsearch
kubectl set env deployment/reranker --containers="goreranker" LOG_LEVEL=error -nsearch
#./monitor-reranker-logs.sh
sudo ./reranker-log-daemon.sh start
for file in reranker-logs/reranker-*.log; do python3 extract_requests.py -i "$file" -o "reranker-logs/requests_$(basename "$file" .log).jsonl"; done

# aws s3 ls s3://unbxd-des/rerankerloadtest/
# aws s3 cp . s3://unbxd-des/rerankerloadtest/gcpuslogs/ --recursive --exclude "*" --include "*.jsonl"
# aws s3 cp s3://unbxd-des/rerankerloadtest/gcpuslogs/ . --recursive --exclude "*" --include "*.jsonl"
