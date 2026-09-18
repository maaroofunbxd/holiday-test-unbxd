#!/bin/bash
# ============================================================================
# HOLIDAY - Automated multi-service holiday load testing
# ============================================================================
# Usage:
#   ./holiday.sh list
#   ./holiday.sh run <service> <region> [options]
#   ./holiday.sh prepare <service> <region>
#   ./holiday.sh report <service> <region> [--dir DIR] [--s3]
#   ./holiday.sh status <service> <region>
#
# Examples:
#   ./holiday.sh run qcs ap-southeast-1prod --rps 50 --duration 5m
#   ./holiday.sh run ner-demo use-1d --background --prepare --stress
#   ./holiday.sh run reranker gcp-us --skip-pre-test
#   ./holiday.sh report qcs ap-southeast-1prod --s3
# ============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if ! command -v python3 >/dev/null 2>&1; then
  echo "error: python3 is required" >&2
  exit 1
fi

usage() {
  cat <<'EOF'
Holiday load-test automation

Commands:
  list                              Show cataloged services
  run SERVICE REGION [options]      Pre-test + monitor + k6 (+ optional prepare)
  prepare SERVICE REGION            Download logs from S3 and extract JSONL
  report SERVICE REGION [options]   Build an HTML dashboard from local or S3 results
  status SERVICE REGION             Check monitor + k6 status

Run options:
  --skip-pre-test                   Do not sync demo from prod
  --skip-monitor                    Do not start pod resource monitoring
  --skip-load                       Do not start k6
  --prepare                         Download + extract payloads before k6
  --background / -b                 Detach monitor and k6 (laptop can close)
  --rps N                           Constant-arrival RPS (default from catalog)
  --duration 5m|600                 k6 duration (monitor duration follows)
  --stress                          Ramp to max RPS instead of flat load
  --start-rps N --max-rps N         Stress ramp bounds
  --ramp 5m --hold 2m               Stress ramp / hold durations
  --namespace NS                    Override catalog namespace
  --host URL                        Skip cluster host discovery
  --k6-script FILE                  Override k6 script

Report options:
  --dir DIR                         Local directory of k6/monitor files
  --s3                              Download latest results from S3 first
  --open                            Print the dashboard path (open it yourself)

SERVICE can be a catalog id or alias (qcs, qcs-demo, reranker-demo, ...).
REGION is an accesscluster.sh region (ap-southeast-1prod, use-1d, gcp-us, ...).
EOF
}

duration_to_seconds() {
  local d="${1:-}"
  if [[ "$d" =~ ^[0-9]+$ ]]; then
    echo "$d"
  elif [[ "$d" =~ ^([0-9]+)s$ ]]; then
    echo "${BASH_REMATCH[1]}"
  elif [[ "$d" =~ ^([0-9]+)m$ ]]; then
    echo $((BASH_REMATCH[1] * 60))
  elif [[ "$d" =~ ^([0-9]+)h$ ]]; then
    echo $((BASH_REMATCH[1] * 3600))
  else
    echo 600
  fi
}

load_service() {
  local name="$1"
  local region="${2:-}"
  if [ -n "$region" ]; then
    eval "$(python3 "$ROOT/services.py" export-env "$name" --region "$region")"
  else
    eval "$(python3 "$ROOT/services.py" export-env "$name")"
  fi
}

cmd_list() {
  python3 "$ROOT/services.py" list
}

cmd_prepare() {
  local name="${1:-}"
  local region="${2:-}"
  if [ -z "$name" ] || [ -z "$region" ]; then
    echo "Usage: ./holiday.sh prepare SERVICE REGION" >&2
    exit 1
  fi
  load_service "$name" "$region"
  echo "Preparing JSONL payloads for $SERVICE_DISPLAY ($SERVICE_ID) in $region"
  echo "  logs dir: $LOGS_DIR"
  echo "  s3 logs:  $S3_LOGS_URI"

  local remote
  remote=$(cat <<EOF
set -e
cd ~/mrf/loadtest/holiday-test-unbxd
git fetch origin >/dev/null 2>&1 || true
git rebase origin/main >/dev/null 2>&1 || true
sh ./downloadfroms3.sh $LOG_PREFIX $LOG_REGION
sh ./process_logs.sh $LOGS_DIR $LOG_PREFIX $SERVICE_ID $LOG_REGION
echo "JSONL files:"
ls -l $LOGS_DIR/*.jsonl 2>/dev/null || echo "(none yet)"
EOF
)
  ./accessloadtestcluster.sh "$remote"
}

write_load_commands() {
  local outfile="$1"
  if [ "${PAYLOAD_MODE:-jsonl}" = "script" ]; then
    cat > "$outfile" <<EOF
export REGION='$LOG_REGION'
python3 ${RUNNER:-autosuggest_test.py}
EOF
    return
  fi
  if [ "${STRESS:-false}" = true ]; then
    cat > "$outfile" <<EOF
export REGION='$LOG_REGION'
export SERVICE='$LOG_PREFIX'
export S3_BUCKET='$S3_BUCKET'
export S3_PREFIX='$S3_PREFIX'
export PAYLOAD_MODE='$PAYLOAD_MODE'
./run-stress-test.sh ${START_RPS} ${MAX_RPS} ${RAMP} ${HOLD} \$HOST $LOG_PREFIX $K6_STRESS_SCRIPT
EOF
  else
    cat > "$outfile" <<EOF
export REGION='$LOG_REGION'
export SERVICE='$LOG_PREFIX'
export S3_BUCKET='$S3_BUCKET'
export S3_PREFIX='$S3_PREFIX'
export PAYLOAD_MODE='$PAYLOAD_MODE'
./k6run.sh ${RPS} ${DURATION} \$HOST $LOG_PREFIX $K6_SCRIPT
EOF
  fi
}

cmd_run() {
  local name="${1:-}"
  local region="${2:-}"
  shift 2 || true

  SKIP_PRE_TEST=false
  SKIP_MONITOR=false
  SKIP_LOAD=false
  PREPARE=false
  BACKGROUND=false
  STRESS=false
  HOST_OVERRIDE=""
  NS_OVERRIDE=""
  SCRIPT_OVERRIDE=""
  RPS=""
  DURATION=""
  START_RPS=""
  MAX_RPS=""
  RAMP=""
  HOLD=""

  while [ $# -gt 0 ]; do
    case "$1" in
      --skip-pre-test) SKIP_PRE_TEST=true; shift ;;
      --skip-monitor) SKIP_MONITOR=true; shift ;;
      --skip-load) SKIP_LOAD=true; shift ;;
      --prepare) PREPARE=true; shift ;;
      -b|--background) BACKGROUND=true; shift ;;
      --stress) STRESS=true; shift ;;
      --rps) RPS="$2"; shift 2 ;;
      --duration) DURATION="$2"; shift 2 ;;
      --start-rps) START_RPS="$2"; shift 2 ;;
      --max-rps) MAX_RPS="$2"; shift 2 ;;
      --ramp) RAMP="$2"; shift 2 ;;
      --hold) HOLD="$2"; shift 2 ;;
      --namespace) NS_OVERRIDE="$2"; shift 2 ;;
      --host) HOST_OVERRIDE="$2"; shift 2 ;;
      --k6-script) SCRIPT_OVERRIDE="$2"; shift 2 ;;
      -h|--help) usage; exit 0 ;;
      *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
    esac
  done

  if [ -z "$name" ] || [ -z "$region" ]; then
    echo "Usage: ./holiday.sh run SERVICE REGION [options]" >&2
    exit 1
  fi

  load_service "$name" "$region"
  NAMESPACE="${NS_OVERRIDE:-$NAMESPACE}"
  RPS="${RPS:-$DEFAULT_RPS}"
  DURATION="${DURATION:-$DEFAULT_DURATION}"
  START_RPS="${START_RPS:-0}"
  MAX_RPS="${MAX_RPS:-60}"
  RAMP="${RAMP:-5m}"
  HOLD="${HOLD:-2m}"
  if [ -n "$SCRIPT_OVERRIDE" ]; then
    K6_SCRIPT="$SCRIPT_OVERRIDE"
    K6_STRESS_SCRIPT="$SCRIPT_OVERRIDE"
  fi

  local monitor_secs
  if [ "$STRESS" = true ]; then
    monitor_secs=$(( $(duration_to_seconds "$RAMP") + $(duration_to_seconds "$HOLD") + 90 ))
  else
    monitor_secs=$(( $(duration_to_seconds "$DURATION") + 60 ))
  fi

  echo ""
  echo "HOLIDAY RUN"
  echo "════════════════════════════════════════════════════════════"
  echo "  Service:     $SERVICE_DISPLAY ($SERVICE_ID)"
  echo "  k8s:         $K8S_SERVICE  ns=$NAMESPACE  label=$APP_LABEL"
  echo "  Region:      $region  (logs=$LOG_REGION)"
  echo "  Payload:     $PAYLOAD_MODE"
  echo "  k6:          $([ "$STRESS" = true ] && echo "stress $START_RPS->$MAX_RPS $K6_STRESS_SCRIPT" || echo "flat ${RPS}rps ${DURATION} $K6_SCRIPT")"
  echo "  Monitor:     ${monitor_secs}s"
  echo "  S3 results:  $S3_BUCKET"
  echo "  Background:  $BACKGROUND"
  echo "════════════════════════════════════════════════════════════"
  echo ""

  if [ "$SKIP_PRE_TEST" != true ]; then
    echo "Step: pre-test (sync demo from prod)"
    local pre_cmd="python3 ./commonpre-test.py --service $SERVICE_ID --namespace $NAMESPACE --replicas $DEMO_REPLICAS"
    if [ "$PRE_TEST_SYNC" = true ]; then
      ./accesscluster.sh "$region" "$pre_cmd"
    else
      echo "  catalog pre_test_sync=false — skipping image sync"
    fi
    if [ -n "$EXTRA_PRE_TEST" ] && [ -f "$EXTRA_PRE_TEST" ]; then
      echo "  extra pre-test: $EXTRA_PRE_TEST"
      ./accesscluster.sh "$region" "bash ./$EXTRA_PRE_TEST"
    fi
  else
    echo "Step: pre-test skipped"
  fi

  if [ "$PREPARE" = true ]; then
    echo "Step: prepare payloads"
    cmd_prepare "$SERVICE_ID" "$region"
  fi

  if [ "$SKIP_MONITOR" != true ]; then
    echo "Step: start monitoring"
    if [ "$BACKGROUND" = true ]; then
      ./monitor.sh --background "$APP_LABEL" "$region" "$NAMESPACE" "$monitor_secs"
    else
      echo "  (interactive) starting monitor in this terminal after printing load-test command"
    fi
  fi

  if [ "$SKIP_LOAD" != true ]; then
    local cmd_file
    cmd_file="$(mktemp "${TMPDIR:-/tmp}/holiday-load.XXXXXX.sh")"
    write_load_commands "$cmd_file"
    echo "Step: load test"
    echo "  commands file: $cmd_file"
    if [ -n "$HOST_OVERRIDE" ]; then
      export HOST="$HOST_OVERRIDE"
    fi
    if [ "$BACKGROUND" = true ]; then
      if [ -n "$HOST_OVERRIDE" ]; then
        HOST="$HOST_OVERRIDE" ./loadtest.sh --background "$K8S_SERVICE" "$region" "$NAMESPACE" "$cmd_file"
      else
        ./loadtest.sh --background "$K8S_SERVICE" "$region" "$NAMESPACE" "$cmd_file"
      fi
    elif [ "$SKIP_MONITOR" = true ]; then
      ./loadtest.sh "$K8S_SERVICE" "$region" "$NAMESPACE" "$cmd_file"
    else
      echo ""
      echo "Interactive mode: monitor + load need two terminals, or re-run with --background."
      echo "  Terminal 1: ./monitor.sh $APP_LABEL $region $NAMESPACE $monitor_secs"
      echo "  Terminal 2: ./loadtest.sh $K8S_SERVICE $region $NAMESPACE $cmd_file"
      echo ""
      echo "Starting monitoring in this terminal. Run the loadtest command in another."
      ./monitor.sh "$APP_LABEL" "$region" "$NAMESPACE" "$monitor_secs"
    fi
  fi

  echo ""
  echo "After the run:"
  echo "  ./holiday.sh status $SERVICE_ID $region"
  echo "  ./holiday.sh report $SERVICE_ID $region --s3 --open"
}

cmd_status() {
  local name="${1:-}"
  local region="${2:-}"
  if [ -z "$name" ] || [ -z "$region" ]; then
    echo "Usage: ./holiday.sh status SERVICE REGION" >&2
    exit 1
  fi
  load_service "$name" "$region"
  ./monitor.sh --status "$region" || true
  ./loadtest.sh --status || true
}

cmd_report() {
  local name="${1:-}"
  local region="${2:-}"
  shift 2 || true
  local dir=""
  local from_s3=false
  local open_dash=false
  while [ $# -gt 0 ]; do
    case "$1" in
      --dir) dir="$2"; shift 2 ;;
      --s3) from_s3=true; shift ;;
      --open) open_dash=true; shift ;;
      *) echo "Unknown option: $1" >&2; exit 1 ;;
    esac
  done
  if [ -z "$name" ] || [ -z "$region" ]; then
    echo "Usage: ./holiday.sh report SERVICE REGION [--dir DIR] [--s3] [--open]" >&2
    exit 1
  fi
  load_service "$name" "$region"
  dir="${dir:-$ROOT/reports/${SERVICE_ID}-${LOG_REGION}}"
  mkdir -p "$dir"
  if [ "$from_s3" = true ]; then
    echo "Downloading results from $S3_BUCKET"
    aws s3 sync "$S3_BUCKET" "$dir" --exclude "*" \
      --include "*summary.json" --include "*raw*.json" --include "*.csv" \
      --include "*stress-test*.json" || true
  fi
  python3 "$ROOT/dashboard.py" --service "$SERVICE_ID" --region "$LOG_REGION" \
    --dir "$dir" --datadog "$DATADOG_DASHBOARD"
  local html="$dir/index.html"
  echo "Dashboard: $html"
  if [ "$open_dash" = true ] && [ -f "$html" ]; then
    if command -v open >/dev/null 2>&1; then
      open "$html"
    else
      echo "Open $html in a browser"
    fi
  fi
}

COMMAND="${1:-}"
shift || true
case "$COMMAND" in
  list) cmd_list "$@" ;;
  run) cmd_run "$@" ;;
  prepare) cmd_prepare "$@" ;;
  report|dashboard) cmd_report "$@" ;;
  status) cmd_status "$@" ;;
  -h|--help|help|"") usage ;;
  *) echo "Unknown command: $COMMAND" >&2; usage; exit 1 ;;
esac
