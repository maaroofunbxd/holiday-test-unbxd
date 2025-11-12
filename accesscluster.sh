#if from local run 
#ssh ec2-user@usejump.unbxd.io "bash -s" -- < ./accesscluster.sh "pwd"

#!/bin/bash
# Interactive access to cluster - lands in holiday-test-unbxd directory
# 
# Usage: ./accesscluster.sh [REGION] [script_to_run|@file]
# 
# Supported regions: ap-southeast-1 (default), use-1d, gcp-us
#
# Examples:
#   ./accesscluster.sh                           # Interactive mode (ap-southeast-1)
#   ./accesscluster.sh use-1d "./clustermonitor.sh"  # Run with specific region
#   ./accesscluster.sh use-1d @commands.txt      # Read commands from file with region
#   ./accesscluster.sh gcp-us "aws s3 ls s3://unbxd-des/"  # Run on GCP with AWS CLI
#   ./accesscluster.sh ap-southeast-1 "kubectl get pods -n search"  # Run kubectl command
#source ../codesnippet/.env && ./accesscluster.sh gcp-us
REGION=${1:-ap-southeast-1}

# Check if second argument starts with @ (file reference)
if [[ "${2}" == @* ]]; then
  # Remove @ prefix and read from file
  CMD_FILE="${2:1}"
  if [ -f "$CMD_FILE" ]; then
    CMD=$(cat "$CMD_FILE")
    echo "Reading commands from file: $CMD_FILE"
  else
    echo "Error: File not found: $CMD_FILE"
    exit 1
  fi
else
  CMD="${2}"
fi

# Set region-specific SSH access
if [ "$REGION" = "use-1d" ]; then
  SSH_HOST="ai"
  SSH_USER="ai-prod-us-east-1-eks"
  SSH_TYPE="standard"
elif [ "$REGION" = "ap-southeast-1" ]; then
  SSH_HOST="10.204.19.93"
  SSH_USER="ai-ap-southeast-1-eks"
  SSH_TYPE="standard"
elif [ "$REGION" = "gcp-us" ]; then
  GCP_INSTANCE="pilot-rc-unbxd-mgmt-host-us-est4-a-gce"
  GCP_ZONE="us-east4-a"
  GCP_PROJECT="unbxdgcp"
  GCP_USER="prod-unbxdgcp-ai02-gke"
  SSH_TYPE="gcloud"
elif [ "$REGION" = "eu-west-2" ]; then
  SSH_HOST="10.210.0.92"
  SSH_USER="ai-prod-eu-west-2-eks"
  SSH_TYPE="standard"
else
  echo "Error: Unsupported region '$REGION'. Supported regions: use-1d, ap-southeast-1, gcp-us"
  exit 1
fi

if [ "$SSH_TYPE" = "gcloud" ]; then
  echo "Using REGION=$REGION (GCP: $GCP_INSTANCE, Zone: $GCP_ZONE)"
else
  echo "Using REGION=$REGION (SSH: $SSH_HOST, User: $SSH_USER)"
fi

# Prepare environment variables to pass through SSH
ENV_VARS=""
if [ -n "$AWS_ACCESS_KEY_ID" ]; then
  ENV_VARS="$ENV_VARS export AWS_ACCESS_KEY_ID='$AWS_ACCESS_KEY_ID';"
fi
if [ -n "$AWS_SECRET_ACCESS_KEY" ]; then
  ENV_VARS="$ENV_VARS export AWS_SECRET_ACCESS_KEY='$AWS_SECRET_ACCESS_KEY';"
fi

if [ "$SSH_TYPE" = "gcloud" ]; then
  # GCP gcloud SSH access
  GCP_TARGET="$GCP_USER@$GCP_INSTANCE"
  if [ -z "$CMD" ]; then
    # Interactive mode
    echo "Entering interactive mode on GCP cluster..."
    echo "Connecting as: $GCP_TARGET"
    echo "Suggested commands:"
    echo "  aws s3 ls s3://unbxd-des/        # List S3 bucket"
    echo "  kubectl get pods -n search       # List pods"
    echo ""
    gcloud beta compute ssh --zone "$GCP_ZONE" --tunnel-through-iap --project "$GCP_PROJECT" "$GCP_TARGET" -- -t "cd ~/mrf/holiday-test-unbxd && $ENV_VARS exec bash"
  else
    # Run specific command/script
    gcloud beta compute ssh --zone "$GCP_ZONE" --tunnel-through-iap --project "$GCP_PROJECT" "$GCP_TARGET" -- -t "cd ~/mrf/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && $ENV_VARS ${CMD}"
  fi
else
  # Standard SSH access (use-1d, ap-southeast-1)
  if [ -z "$CMD" ]; then
    # Interactive mode - no command provided
    echo "Entering interactive mode on cluster..."
    echo "Suggested commands:"
    echo "  ./clustermonitor.sh              # Monitor pods"
    echo "  ./get-service-host.sh reranker   # Get reranker host"
    echo "  kubectl get pods -n search       # List pods"
    echo ""
    ssh -t ec2-user@usejump.unbxd.io "ssh -t $SSH_HOST \"sudo su - $SSH_USER -c 'cd ~/mrf/holiday-test-unbxd && exec bash'\""
  else
    # Run specific command/script
    ssh -t ec2-user@usejump.unbxd.io "ssh -t $SSH_HOST \"sudo su - $SSH_USER -c 'cd ~/mrf/holiday-test-unbxd && git fetch origin >/dev/null 2>&1 && git rebase origin/main >/dev/null 2>&1 && ${CMD}'\""
  fi
fi

#REGION=use-1d sh accesscluster.sh 'whoami'

#./accesscluster.sh  use-1d 'git fetch origin && git rebase origin/main'