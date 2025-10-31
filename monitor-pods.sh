#!/bin/bash
# Monitor Kubernetes pods with resource usage as fractions

echo "POD_NAME                          CPU_REQUEST/LIMIT       MEMORY_REQUEST/LIMIT"
echo "====================================================================================

kubectl top pods -l'algo in (personalization,ranking)' --no-headers | while read -r line; do
    POD_NAME=$(echo "$line" | awk '{print $1}')
    CPU_CURRENT=$(echo "$line" | awk '{print $2}')
    MEM_CURRENT=$(echo "$line" | awk '{print $3}')
    
    # Get pod resource requests and limits
    RESOURCES=$(kubectl get pod "$POD_NAME" -o json | jq -r '.spec.containers[0].resources')
    
    CPU_REQUEST=$(echo "$RESOURCES" | jq -r '.requests.cpu // "N/A"')
    CPU_LIMIT=$(echo "$RESOURCES" | jq -r '.limits.cpu // "N/A"')
    MEM_REQUEST=$(echo "$RESOURCES" | jq -r '.requests.memory // "N/A"')
    MEM_LIMIT=$(echo "$RESOURCES" | jq -r '.limits.memory // "N/A"')
    
    # Format output
    printf "%-35s %-25s %-25s\n" \
        "$POD_NAME" \
        "$CPU_CURRENT/$CPU_LIMIT (req:$CPU_REQUEST)" \
        "$MEM_CURRENT/$MEM_LIMIT (req:$MEM_REQUEST)"
done

