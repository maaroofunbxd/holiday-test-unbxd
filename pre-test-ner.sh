helm get values ner -nsearch -o yaml > ner-prod-values.yaml

cd ~/mrf/entity-extraction/;
helm template ner-demo ./helm/ner -nsearch\
  -f ner-prod-values.yaml \
  --set service.name=ner-demo \
  --set env=demo \
  --set app=ner-demo \
  --set replicaCount=1 \
  --set service.type=LoadBalancer \
  --set albus.nats_service=ner-demo \
  --set deployment.env.ELASTIC_APM_SERVICE_NAME=ner-demo \
  --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-name"=ner-demo-lb \
  --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-additional-resource-tags"="Environment=demo,Service=ner-demo" \
  --no-hooks \
  > ner-demo-manifests.yaml

helm install ner-demo ./helm/ner -nsearch\
  -f ner-prod-values.yaml \
  --set service.name=ner-demo \
  --set env=demo \
  --set app=ner-demo \
  --set replicaCount=1 \
  --set service.type=LoadBalancer \
  --set albus.nats_service=ner-demo \
  --set deployment.env.ELASTIC_APM_SERVICE_NAME=ner-demo \
  --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-name"=ner-demo-lb \
  --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-additional-resource-tags"="Environment=demo,Service=ner-demo" \
  --no-hooks \
 --dry-run

helm install ner-demo ./helm/ner -nsearch\
  -f ner-prod-values.yaml \
  --set service.name=ner-demo \
  --set env=demo \
  --set app=ner-demo \
  --set replicaCount=1 \
  --set service.type=LoadBalancer \
  --set albus.nats_service=ner-demo \
  --set deployment.env.ELASTIC_APM_SERVICE_NAME=ner-demo \
  --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-name"=ner-demo-lb \
  --set service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-additional-resource-tags"="Environment=demo,Service=ner-demo" \
  --no-hooks
