#!/bin/bash
# Usage: ./get-service-host.sh <service-name> <ns>
# Gets the load balancer hostname or IP for a service

SERVICE=${1:-reranker-demo}
namespace=${2:-search}
# Try to get hostname first
HOST=$(kubectl get svc $SERVICE -n $namespace -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null)

# If hostname is empty, try to get IP
if [ -z "$HOST" ]; then
    HOST=$(kubectl get svc $SERVICE -n $namespace -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
fi

# Output the HOST (no http:// prefix, add that when using it)
echo "$HOST"






