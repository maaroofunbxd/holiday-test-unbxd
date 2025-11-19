deploymentname="qcs"
containername="qcs"
namespace="ai"
#TO GET the prod logs
# kubectl set env deploy/$deploymentname -n$namespace --list --resolve
# kubectl set env deployment/$deploymentname -n$namespace --containers=$containername LOG_LEVEL=DEBUG
# kubectl annotate deploy $deploymentname -n $namespace \
#   kubernetes.io/change-cause="$containername debugging "

# kubectl rollout status deployment $deploymentname -n$namespace
# kubectl rollout history deployment $deploymentname -n$namespace


# kubectl get deploy $deploymentname-demo -n$namespace -oyaml > demo.yaml
# kubectl get deploy $deploymentname -n$namespace -oyaml > prod.yaml

# exit 0

#in local
diff demo.yaml prod.yaml

SOURCE_IMAGE=$(kubectl get deployment $deploymentname -n$namespace -o jsonpath="{.spec.template.spec.containers[?(@.name=='$containername')].image}")
echo "SOURCE_IMAGE: $SOURCE_IMAGE"
CURRENT_IMAGE=$(kubectl get deployment $deploymentname-demo -n$namespace -o jsonpath="{.spec.template.spec.containers[?(@.name=='$containername')].image}")
echo "CURRENT_IMAGE: $CURRENT_IMAGE"
kubectl set image deployment/$deploymentname-demo -n$namespace $containername=$SOURCE_IMAGE

POLICY=$(kubectl get deploy $deploymentname -n$namespace -o jsonpath='{.spec.template.spec.containers[?(@.name=='$containername')].imagePullPolicy}')
kubectl patch deploy $deploymentname-demo -n$namespace -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[{\"name\":\"$containername\",\"imagePullPolicy\":\"$POLICY\"}]}}}}"
kubectl get deploy $deploymentname-demo -n$namespace -o jsonpath='{.spec.template.spec.containers[?(@.name=='$containername')].imagePullPolicy}'



# 1️⃣ Extract container config from source
CONTAINER=$(kubectl get deploy $deploymentname -n$namespace -o json | jq -c '.spec.template.spec.containers[] | select(.name=='$containername') | {name,resources,livenessProbe,readinessProbe}')

# 2️⃣ Print existing target container values before patching
echo "---- Current target values ----"
kubectl get deploy $deploymentname-demo -n$namespace -o json | jq '.spec.template.spec.containers[] | select(.name=='$containername') | {name,resources,livenessProbe,readinessProbe}'

# 3️⃣ Patch the target with the copied specs
kubectl patch deploy $deploymentname-demo -n$namespace -p "{\"spec\":{\"template\":{\"spec\":{\"containers\":[${CONTAINER}]}}}}"


# 4️⃣ Confirm new values
echo "---- Updated target values ----"
kubectl get deploy $deploymentname-demo -o json | jq '.spec.template.spec.containers[] | select(.name=='$containername') | {name,resources,livenessProbe,readinessProbe}'

kubectl get deploy $deploymentname-demo -n$namespace -o jsonpath='{.spec.template.spec.containers[?(@.name=='$containername')].livenessProbe}'
kubectl get deploy $deploymentname-demo -n$namespace -o jsonpath='{.spec.template.spec.containers[?(@.name=='$containername')].readinessProbe}'
kubectl get deploy $deploymentname-demo -n$namespace -o jsonpath='{.spec.template.spec.containers[?(@.name=='$containername')].resources}'



#kubectl set env deployment/$deploymentname -n$namespace --containers="$containername" LOG_LEVEL=error
# kubectl set env deployment/$deploymentname -n$namespace --containers="$containername" LOG_LEVEL=ERROR
# kubectl annotate deploy $deploymentname -n $namespace \
#   kubernetes.io/change-cause="reset"
# kubectl rollout status deployment $deploymentname -n$namespace
# kubectl rollout history deployment $deploymentname -n$namespace


replicas=$(kubectl get deploy $deploymentname -n$namespace -o jsonpath='{.spec.replicas}')
#apse1
kubectl scale deploy $deploymentname-demo -n$namespace --replicas=1

kubectl annotate deploy $deploymentname-demo -n search \
  kubernetes.io/change-cause="increased replicas to $replicas"


kubectl rollout restart deployment $deploymentname-demo -n$namespace
kubectl rollout status deployment $deploymentname-demo -n$namespace
kubectl rollout history deployment $deploymentname-demo -n$namespace
# kubectl rollout undo deployment $deploymentname-demo -n$namespace
# kubectl rollout undo deployment $deploymentname-demo -n$namespace --to-revision=1
diff demo.yaml prod.yaml