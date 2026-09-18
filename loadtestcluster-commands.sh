export REGION="${REGION:-ap-southeast-1}"
export SERVICE="${SERVICE:-qcs}"
./k6run.sh ${RPS:-50} ${DURATION:-5m} $HOST ${SERVICE} ${K6_SCRIPT:-reranker-load-test.js}
