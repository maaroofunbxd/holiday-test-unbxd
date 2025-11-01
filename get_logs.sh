#!/bin/bash

# Default configuration
DEFAULT_NAMESPACE="search"
DEFAULT_OUTPUT_FILE="pod_logs.txt"

# Function to get logs for one pod and append to file
get_pod_logs() {
  local pod_name=$1
  local namespace=${2:-$DEFAULT_NAMESPACE}
  local output_file=${3:-$DEFAULT_OUTPUT_FILE}
  local container=${4:-""}  # Optional container name

  if [[ -z "$pod_name" ]]; then
    echo "❌ pod_name is required"
    return 1
  fi

  echo ">>> Getting logs for pod: $pod_name container: $container (namespace: $namespace)" | tee -a "$output_file"
  kubectl logs -n "$namespace" "$pod_name" -c $container >> "$output_file" 2>&1
  echo -e "\n" >> "$output_file"
}

# Function to get all pods by label
get_all_pods_by_label() {
  local label_selector=${1:-"app=r"}
  local namespace=${2:-$DEFAULT_NAMESPACE}
  kubectl get pods -n "$namespace" -l "$label_selector" -o jsonpath='{.items[*].metadata.name}'
}

# Main driver
main() {
  local namespace=${1:-$DEFAULT_NAMESPACE}
  local label_selector=${2:-"app=reranker"}
  local output_file=${3:-$DEFAULT_OUTPUT_FILE}
  local container=${4:-""}  # Optional container name

  > "$output_file"  # clear file first
  local pods
  pods=$(get_all_pods_by_label "$label_selector" "$namespace")

  for pod in $pods; do
    get_pod_logs "$pod" "$namespace" "$output_file" "$container"
  done

  echo "✅ Logs saved to $output_file"
}

main "$@"
#sh get_logs.sh search "app=reranker-demo" "pod_logs.txt" "pyreranker"
