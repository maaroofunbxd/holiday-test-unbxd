// 🔥 Universal Stress Test - Find maximum RPS for any service
// Gradually ramps up RPS to find the breaking point
// Supports: reranker, ner, qcs, and custom services
// Uses standardized payload format: type (get/post), query_string, payload, sitekey
import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { check, sleep } from 'k6';
import { getUrlBuilder } from './service-configs.js';

// ✅ Get host from environment variable or use default
const HOST = __ENV.HOST || 'http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com';

// ✅ Get input files from environment variable or use default
const inputFiles = (__ENV.INPUT_FILES || 'extracted_payloads_py.jsonl').split(',').map(f => f.trim());

// ✅ Get base path for files
const BASE_PATH = __ENV.BASE_PATH !== undefined ? __ENV.BASE_PATH : '.';

// 🔧 Generic URL builder - works with any service
const URL_BUILDER = getUrlBuilder();

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

  // Build request configuration using the URL builder
  const requestConfig = URL_BUILDER(HOST, randomPayload);
  
  if (!requestConfig) {
    console.warn('⚠️  Could not build request config for payload');
    return;
  }

  const params = {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',  // Prevent hanging requests
  };

  // Execute request based on method
  let response;
  if (requestConfig.method === 'GET') {
    response = http.get(requestConfig.url, params);
  } else if (requestConfig.method === 'POST') {
    response = http.post(requestConfig.url, requestConfig.body, params);
  } else if (requestConfig.method === 'PUT') {
    response = http.put(requestConfig.url, requestConfig.body, params);
  } else {
    console.warn(`⚠️  Unsupported method: ${requestConfig.method}`);
    return;
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
  if (metrics.http_req_duration && metrics.http_req_duration.values) {
    console.log(`⏱️  Response times:`);
    const p50 = metrics.http_req_duration.values['p(50)'];
    const p95 = metrics.http_req_duration.values['p(95)'];
    const p99 = metrics.http_req_duration.values['p(99)'];
    const max = metrics.http_req_duration.values.max;
    
    if (p50 !== undefined && p50 !== null) {
      console.log(`   - p50: ${p50.toFixed(2)}ms`);
      console.log(`   - p95: ${p95.toFixed(2)}ms`);
      console.log(`   - p99: ${p99.toFixed(2)}ms`);
      console.log(`   - max: ${max.toFixed(2)}ms`);
    } else {
      console.log(`   - No response time data (no successful requests)`);
    }
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
