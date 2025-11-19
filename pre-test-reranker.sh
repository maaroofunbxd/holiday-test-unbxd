

#sudo  ./log-daemon.sh start app=reranker ./reranker-gcp-us-logs search 30 6
#sudo ./log-daemon.sh stop app=reranker

# last years (2024) reranker go use-1d showing much larger RPS for use-1d than now : max -> (20,0.1)
# reranker2024:
#     go:
#         rps:
#             max: 20
            
# https://docs.google.com/spreadsheets/d/1HwN-W9mj1CcGNLGZNTpzbyFk-dG8ZJoOBkCnn54sWy8/edit?gid=0#gid=0
# https://app.datadoghq.com/dashboard/dbd-x57-fig/reranker?fromUser=true&fullscreen_end_ts=1762159766854&fullscreen_paused=false&fullscreen_refresh_mode=sliding&fullscreen_section=overview&fullscreen_start_ts=1761554966854&fullscreen_widget=8411901009295312&refresh_mode=sliding&tpl_var_region%5B0%5D=us-east-1&from_ts=1762073314258&to_ts=1762159714258&live=true


sudo su - ai-prod-us-east-1-eks
kubectl get configmap  reranker-demo-envoy -nsearch -oyaml > olddemoconfigmap.yaml
kubectl get configmap reranker-envoy -nsearch -o json | jq '{data: .data}' > tmp.json
kubectl patch configmap reranker-demo-envoy -nsearch --type merge -p "$(cat tmp.json)"
#edit it manually if needed
#kubectl delete configmap reranker-demo-envoy
# cat > democonfigmap.yaml <<EOF
# EOF
#kubectl apply -f democonfigmap.yaml


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


kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" REDIS_CACHE_TTL=80
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" METRICS_TAGS='app:reranker-demo,env:prod,region:ap-southeast-1,version:go'
kubectl set env deployment/reranker-demo -nsearch --containers="goreranker" METRICS_NAMESPACE=reranker-demo
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" ENV=prod
kubectl set env deployment/reranker-demo -nsearch --containers="pyreranker" SERVICE=reranker-demo
#for pyreranker have to change command itself

# kubectl patch deployment reranker-demo -nsearch --type='json' \
#   -p='[{"op": "replace", "path": "/spec/template/spec/containers/0/command", "value": ["/bin/sh", "-c", "python3 /app/reranker/pyreranker.py"]}]'

#before load test
#kubectl set env deploy/reranker-demo -nsearch --list --resolve --containers="pyreranker" | grep -i TTL
