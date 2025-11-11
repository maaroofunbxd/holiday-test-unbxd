#!/bin/bash

echo "=== Debugging StatsD Metrics for ap-southeast-1 ==="
echo ""

echo "1. Checking deployment YAML for Gunicorn StatsD flags:"
kubectl get deployment reranker -n search -o yaml | grep -B2 -A8 "statsd"

echo ""
echo "2. Getting actual running pod:"
POD=$(kubectl get pods -n search -l app=reranker -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)
echo "Pod name: $POD"

echo ""
echo "3. Checking pod's Gunicorn command:"
kubectl get pod $POD -n search -o jsonpath='{.spec.containers[0].command[*]}' | tr ' ' '\n'

echo ""
echo "4. Checking STATSD environment variables in pod:"
kubectl exec $POD -n search -- env | grep -E "STATSD|SERVICE|REGION|ENV" | sort

echo ""
echo "5. Testing network connectivity to StatsD:"
kubectl exec $POD -n search -- sh -c "timeout 2 nc -zv statsd.prod.ap-southeast-1.infra 8125 2>&1 || echo 'Connection failed'"

echo ""
echo "6. Checking if StatsD service is reachable via DNS:"
kubectl exec $POD -n search -- nslookup statsd.prod.ap-southeast-1.infra 2>&1

echo ""
echo "7. Checking pod labels:"
kubectl get pod $POD -n search -o jsonpath='{.metadata.labels}' | jq '.'

echo ""
echo "8. Checking recent logs for StatsD errors:"
kubectl logs $POD -n search --tail=50 | grep -i "statsd\|metric" || echo "No StatsD mentions in recent logs"

echo ""
echo "=== Debug Complete ==="

