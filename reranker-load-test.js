// Universal Load Test - Works with any service (reranker, ner, qcs, etc.)
// Uses standardized payload format: type (get/post), query_string, payload, sitekey
import http from 'k6/http';
import { SharedArray } from 'k6/data';
import { getUrlBuilder } from './service-configs.js';

// ✅ Get host from environment variable or use default
const HOST = __ENV.HOST || 'http://internal-a33ac7ecf86484bdb9a6a550a45a3f8d-2136975334.us-east-1.elb.amazonaws.com';

// ✅ Get input files from environment variable or use default
// Supports comma-separated list: "file1.jsonl,file2.jsonl,file3.jsonl"
const inputFiles = (__ENV.INPUT_FILES || 'extracted_payloads_py.jsonl').split(',').map(f => f.trim());

// ✅ Get base path for files (relative to cwd, not script location)
// Default is '.' (current directory) - input files are relative to pwd
const BASE_PATH = __ENV.BASE_PATH !== undefined ? __ENV.BASE_PATH : '.';

// 🔧 Generic URL builder - works with any service
const URL_BUILDER = getUrlBuilder();

// ✅ Get RPS from environment variable or use default
const RPS = parseInt(__ENV.RPS || '10');

// ✅ Get duration from environment variable or use default
const DURATION = __ENV.DURATION || '2m';

// ✅ Load JSONL files — all entries are JSON with sitekey
const payloads = new SharedArray('payloads', () => {
  let allPayloads = [];
  
  // Load and combine all input files
  inputFiles.forEach(inputFile => {
    // Construct full path: if inputFile is absolute, use as-is; otherwise prepend BASE_PATH
    const filePath = inputFile.startsWith('/') ? inputFile : 
                     (BASE_PATH ? `${BASE_PATH}/${inputFile}` : inputFile);
    console.log("loading file: ", filePath);
    
    const fileContent = open(filePath).trim();
    
    // Skip empty files
    if (!fileContent) {
      console.log("skipping empty file: ", filePath);
      return;
    }
    
    const filePayloads = fileContent
      .split('\n')
      .map(line => JSON.parse(line));
    
    allPayloads = allPayloads.concat(filePayloads);
  });
  
  // // Filter for specific sitekey
  // const targetSitekey = 'hsn-com700091495001458';
  // const filteredPayloads = allPayloads.filter(p => p.sitekey === targetSitekey);
  
  // console.log(`Total payloads loaded: ${allPayloads.length}`);
  // console.log(`Filtered payloads for ${targetSitekey}: ${filteredPayloads.length}`);
  const filteredPayloads = allPayloads;  
  return filteredPayloads;
});

export const options = {
  discardResponseBodies: false,
  scenarios: {
    load_test: {
      executor: 'constant-arrival-rate',
      rate: RPS,            // Configurable flat RPS via RPS env var
      timeUnit: '1s',
      duration: DURATION,   // Configurable duration via DURATION env var
      gracefulStop: '0s',   // Immediately stop iterations when duration ends
      preAllocatedVUs: Math.max(10, RPS * 2),  // Pre-allocate VUs based on RPS
      maxVUs: Math.max(50, RPS * 5),           // Allow scaling based on RPS
    },
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
  };

  // Execute request based on method
  if (requestConfig.method === 'GET') {
    http.get(requestConfig.url, params);
  } else if (requestConfig.method === 'POST') {
    http.post(requestConfig.url, requestConfig.body, params);
  } else if (requestConfig.method === 'PUT') {
    http.put(requestConfig.url, requestConfig.body, params);
  } else {
    console.warn(`⚠️  Unsupported method: ${requestConfig.method}`);
    return;
  }
}
