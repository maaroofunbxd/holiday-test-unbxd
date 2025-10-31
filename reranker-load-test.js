//watch -n 5 kubectl top pods -l algo=personalization
//kubectl top pods -l'algo in (personalization,ranking)' --no-headers
//cat > reranker-load-test.js
import http from 'k6/http';
import { SharedArray } from 'k6/data';

// ✅ Get host from environment variable or use default
const HOST = __ENV.HOST || 'http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com';

// ✅ Get input files from environment variable or use default
// Supports comma-separated list: "file1.jsonl,file2.jsonl,file3.jsonl"
const inputFiles = (__ENV.INPUT_FILES || 'extracted_payloads_py.jsonl').split(',').map(f => f.trim());

// ✅ Load JSONL files — all entries are JSON with sitekey
const payloads = new SharedArray('payloads', () => {
  let allPayloads = [];
  
  // Load and combine all input files
  inputFiles.forEach(inputFile => {
    const filePayloads = open(inputFile)
      .trim()
      .split('\n')
      .map(line => JSON.parse(line));
    
    allPayloads = allPayloads.concat(filePayloads);
  });
  
  return allPayloads;
});

export const options = {
  discardResponseBodies: false,
  scenarios: {
    load_test: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 10,
      maxVUs: 20,
      stages: [
        { target: 10, duration: '1m' },
        { target: 5, duration: '1m' },
      ],
    },
  },
};

export default function () {
  // Randomly select a payload
  const randomPayload = payloads[Math.floor(Math.random() * payloads.length)];

  // Extract sitekey from the JSON entry itself
  const sitekey = randomPayload.sitekey;
  
  if (!sitekey) {
    console.warn('No sitekey found in payload');
    return;
  }

  const params = {
    headers: { 'Content-Type': 'application/json' },
  };

  // Determine request type and route accordingly
  if (randomPayload.query_string) {
    // Query string request - GET /v1.0/sites/.../recommend?...
    let url = `${HOST}/v1.0/sites/${sitekey}/recommend`;
    
    // Append the query string (ensure it starts with ?)
    const queryString = randomPayload.query_string;
    url += queryString.startsWith('?') ? queryString : '?' + queryString;
    
    http.get(url, params);
  } else if (randomPayload.payload) {
    // JSON payload request
    if (randomPayload.payload.rankingContext !== undefined) {
      // With rankingContext - POST /v1.0/sites/.../rerank
      const url = `${HOST}/v1.0/sites/${sitekey}/rerank`;
      http.post(url, JSON.stringify(randomPayload.payload), params);
    } else {
      // Without rankingContext - POST /v2.0/sites/.../recommend
      const url = `${HOST}/v2.0/sites/${sitekey}/recommend`;
      http.post(url, JSON.stringify(randomPayload.payload), params);
    }
  }
}
