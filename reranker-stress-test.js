// 🔥 STRESS TEST CONFIG - Find maximum RPS
// Gradually ramps up RPS to find the breaking point
import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { check, sleep } from 'k6';

// ✅ Get host from environment variable or use default
const HOST = __ENV.HOST || 'http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com';

// ✅ Get input files from environment variable or use default
const inputFiles = (__ENV.INPUT_FILES || 'extracted_payloads_py.jsonl').split(',').map(f => f.trim());

// ✅ Get base path for files
const BASE_PATH = __ENV.BASE_PATH !== undefined ? __ENV.BASE_PATH : '.';

// ✅ Stress test configuration - can be overridden via env vars
const START_RPS = parseInt(__ENV.START_RPS || '10');      // Starting RPS
const MAX_RPS = parseInt(__ENV.MAX_RPS || '500');         // Target max RPS
const RAMP_DURATION = __ENV.RAMP_DURATION || '5m';        // Time to ramp from START to MAX
const HOLD_DURATION = __ENV.HOLD_DURATION || '2m';        // Hold at max for this duration

// ✅ Load JSONL files
const payloads = new SharedArray('payloads', () => {
  let allPayloads = [];
  
  inputFiles.forEach(inputFile => {
    const filePath = inputFile.startsWith('/') ? inputFile : 
                     (BASE_PATH ? `${BASE_PATH}/${inputFile}` : inputFile);
    console.log("📂 Loading file:", filePath);
    
    const fileContent = open(filePath).trim();
    
    if (!fileContent) {
      console.log("⚠️  Skipping empty file:", filePath);
      return;
    }
    
    const filePayloads = fileContent
      .split('\n')
      .map(line => JSON.parse(line));
    
    allPayloads = allPayloads.concat(filePayloads);
  });
  
  console.log(`✅ Total payloads loaded: ${allPayloads.length}`);
  return allPayloads;
});

export const options = {
  discardResponseBodies: true,  // Save memory during stress test
  scenarios: {
    stress_ramp: {
      executor: 'ramping-arrival-rate',
      startRate: START_RPS,
      timeUnit: '1s',
      preAllocatedVUs: Math.max(50, MAX_RPS * 2),
      maxVUs: Math.max(200, MAX_RPS * 5),
      stages: [
        // Ramp up gradually to find breaking point
        { duration: RAMP_DURATION, target: MAX_RPS },
        // Hold at max to see if system stabilizes
        { duration: HOLD_DURATION, target: MAX_RPS },
        // Ramp down gracefully
        { duration: '1m', target: 0 },
      ],
      gracefulStop: '30s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<5000', 'p(99)<10000'],  // 95% under 5s, 99% under 10s
    http_req_failed: ['rate<0.10'],                     // Less than 10% errors
    http_reqs: ['rate>0'],                              // Track actual RPS achieved
  },
};

export default function () {
  // Randomly select a payload
  const randomPayload = payloads[Math.floor(Math.random() * payloads.length)];
  const sitekey = randomPayload.sitekey;
  
  if (!sitekey) {
    console.warn('⚠️  No sitekey found in payload');
    return;
  }

  const params = {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',  // Prevent hanging requests
  };

  let response;

  // Determine request type and route accordingly
  if (randomPayload.query_string) {
    // Query string request - GET /v1.0/sites/.../recommend?...
    let url = `${HOST}/v1.0/sites/${sitekey}/recommend`;
    const queryString = randomPayload.query_string;
    url += queryString.startsWith('?') ? queryString : '?' + queryString;
    response = http.get(url, params);
  } else if (randomPayload.payload) {
    // JSON payload request
    if (randomPayload.payload.rankingContext !== undefined) {
      // With rankingContext - POST /v1.0/sites/.../rerank
      const url = `${HOST}/v1.0/sites/${sitekey}/rerank`;
      response = http.post(url, JSON.stringify(randomPayload.payload), params);
    } else {
      // Without rankingContext - POST /v2.0/sites/.../recommend
      const url = `${HOST}/v2.0/sites/${sitekey}/recommend`;
      response = http.post(url, JSON.stringify(randomPayload.payload), params);
    }
  }

  // Check response quality
  check(response, {
    'status is 200': (r) => r && r.status === 200,
    'response time < 5s': (r) => r && r.timings.duration < 5000,
  });
}

export function handleSummary(data) {
  console.log('\n🎯 STRESS TEST RESULTS:');
  console.log('═══════════════════════════════════════════');
  
  const metrics = data.metrics;
  
  // Calculate actual max RPS achieved
  if (metrics.http_reqs) {
    const totalReqs = metrics.http_reqs.values.count;
    const totalDuration = data.state.testRunDurationMs / 1000; // Convert to seconds
    const avgRPS = (totalReqs / totalDuration).toFixed(2);
    console.log(`📊 Average RPS achieved: ${avgRPS}`);
  }
  
  // Response times
  if (metrics.http_req_duration) {
    console.log(`⏱️  Response times:`);
    console.log(`   - p50: ${metrics.http_req_duration.values['p(50)'].toFixed(2)}ms`);
    console.log(`   - p95: ${metrics.http_req_duration.values['p(95)'].toFixed(2)}ms`);
    console.log(`   - p99: ${metrics.http_req_duration.values['p(99)'].toFixed(2)}ms`);
    console.log(`   - max: ${metrics.http_req_duration.values.max.toFixed(2)}ms`);
  }
  
  // Error rate
  if (metrics.http_req_failed) {
    const errorRate = (metrics.http_req_failed.values.rate * 100).toFixed(2);
    console.log(`❌ Error rate: ${errorRate}%`);
  }
  
  // VUs used
  if (metrics.vus_max) {
    console.log(`👥 Max VUs used: ${metrics.vus_max.values.max}`);
  }
  
  console.log('═══════════════════════════════════════════\n');
  
  return {
    'stdout': JSON.stringify(data, null, 2),
  };
}
