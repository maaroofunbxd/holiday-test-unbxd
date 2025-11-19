#helm get values qcs -nai -o yaml > qcs-prod-values.yaml

cd ~/mrf/qcs/;


#helm uninstall qcs-demo -nai

#git checkout AI-915
#git fetch origin && git rebase origin/AI-915
ls -R ./helm
helm template qcs-demo  ./helm/qcs/ -f ./helm/qcs/values-aws-dev-ap-southeast-1.yaml -nai \
  --set service.env.SERVICE=qcs-demo \
  --set app=qcs-demo \
  --set service.type=LoadBalancer \
  --set service\.beta\.kubernetes\.io/aws-load-balancer-internal="0.0.0.0/0" \
  > qcs-demo-manifests.yaml

# helm install qcs-demo ./helm/qcs -nai\
#   -f qcs-prod-values.yaml \
#   --set service.name=qcs-demo \
#   --set env=demo \
#   --set app=qcs-demo \
#   --set replicaCount=1 \
#   --set service.type=LoadBalancer \
#   --set albus.nats_service=qcs-demo \
#   --set deployment.env.ELASTIC_APM_SERVICE_NAME=qcs-demo \
#   --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-name"=qcs-demo-lb \
#   --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-additional-resource-tags"="Environment=demo,Service=qcs-demo" \
#   --no-hooks \
#  --dry-run

# helm install qcs-demo ./helm/qcs -nai\
#   -f qcs-prod-values.yaml \
#   --set service.name=qcs-demo \
#   --set env=demo \
#   --set app=qcs-demo \
#   --set replicaCount=1 \
#   --set service.type=LoadBalancer \
#   --set albus.nats_service=qcs-demo \
#   --set deployment.env.ELASTIC_APM_SERVICE_NAME=qcs-demo \
#   --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-name"=qcs-demo-lb \
#   --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-additional-resource-tags"="Environment=demo,Service=qcs-demo" \
#   --no-hooks

helm upgrade qcs-demo  ./helm/qcs/ -f ./helm/qcs/values-aws-dev-ap-southeast-1.yaml -nai \
  --set service.env.SERVICE=qcs-demo \
  --set app=qcs-demo \
  --set service.type=LoadBalancer \
  --set service\.beta\.kubernetes\.io/aws-load-balancer-internal="0.0.0.0/0" \
  --set service.env.REDIS_HOST=ub-ec.prod.ap-southeast-1.infra \
  --set service.env.GIMLI_URL=http://odin.prod.ap-southeast-1.infra \
  --set ELASTIC_APM_SERVER_URL=http://apm.pilot-unbxd.infra:8200 \
  --set service.env.ALBUSCLIENT_ALBUS_HOST=http://configstore.prod.ap-southeast-1.infra \
  --set gunicorn.workerConnections=1000
  --set image.tag=PR_maaroofunbxd_AI-915
#helm uninstall qcs-demo -nai