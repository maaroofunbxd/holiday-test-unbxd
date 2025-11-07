cd /home/ai-ap-southeast-1-eks/mrf
alias logfetchstart='cd holiday-test-unbxd/ && sudo ./log-daemon.sh start app=reranker ./reranker-logs'
logfetchstart


# last years (2024) reranker go use-1d showing much larger RPS for use-1d than now : max -> (20,0.1)
# reranker2024:
#     go:
#         rps:
#             max: 20
            
# https://docs.google.com/spreadsheets/d/1HwN-W9mj1CcGNLGZNTpzbyFk-dG8ZJoOBkCnn54sWy8/edit?gid=0#gid=0
# https://app.datadoghq.com/dashboard/dbd-x57-fig/reranker?fromUser=true&fullscreen_end_ts=1762159766854&fullscreen_paused=false&fullscreen_refresh_mode=sliding&fullscreen_section=overview&fullscreen_start_ts=1761554966854&fullscreen_widget=8411901009295312&refresh_mode=sliding&tpl_var_region%5B0%5D=us-east-1&from_ts=1762073314258&to_ts=1762159714258&live=true


cd /home/ai-ap-southeast-1-eks/mrf
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

#CHECK if it is DEBUG or ERROR
# kubectl set env deployment/reranker --containers="pyreranker" LOG_LEVEL=ERROR -nsearch
# kubectl set env deployment/reranker --containers="goreranker" LOG_LEVEL=error -nsearch

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

# 1️⃣ Extract container config from source
CONTAINER=$(kubectl get deploy reranker -nsearch -o json | jq -c '.spec.template.spec.containers[] | select(.name=="pyreranker") | {name,resources,livenessProbe,readinessProbe}')

# 3️⃣ Patch the target with the copied specs
kubectl patch deploy reranker-demo -nsearch -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[${CONTAINER}]}}}}"

# 4️⃣ Confirm new values
echo "---- Updated target values ----"
kubectl get deploy reranker-demo -o json | jq '.spec.template.spec.containers[] | select(.name=="goreranker") | {name,resources,livenessProbe,readinessProbe}'

kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].livenessProbe}'
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].readinessProbe}'
kubectl get deploy reranker-demo -nsearch -o jsonpath='{.spec.template.spec.containers[?(@.name=="goreranker")].resources}'


#aws apse1
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" ARAGORN_HOST='http://aragorn:80'
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" CACHE_HOST=''
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" DOCSTORE_FILTER_TIMEOUT='600'
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" OLYMPUS_HOST='http://olympus.prod.ap-southeast-1.infra'
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" VISION_TIMEOUT=10000
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" LOG_LEVEL=error


kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ALBUSCLIENT_ENABLE_HANDLER_CACHE='false'
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ALBUSCLIENT_ENABLE_PROPERTY_CACHE='false'
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ALBUSCLIENT_NATS_HOSTS='nats://nats-bridge-internal.prod.ap-southeast-1.infra:4222'
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ASTERIX_ENDPOINT='http://asterix.pilot-rc-unbxd.infra'
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ALBUSCLIENT_SOCKET_TIMEOUT='1200'
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" DOCSTORE_TIMEOUT='0.6'
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" IS_PIPELINES_IFSVC_TIMEOUT=5


kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" LOG_LEVEL=ERROR
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_CONNECT_TIMEOUT=100
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_CONNECT_TIMEOUT_RERANKER=0.05
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_SOCKET_TIMEOUT_RERANKER=0.1



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



#before load test
kubectl set env deploy/reranker-demo -nsearch --list --resolve --containers="pyreranker" | grep -i TTL

./process_reranker_logs.sh ner-logs ner-