// 🔥 STRESS TEST CONFIG - Find maximum RPS
export const options = {
    discardResponseBodies: false,
    scenarios: {
      stress_test: {
        executor: 'shared-iterations',
        vus: 50,              // Start with 50 concurrent users
        iterations: 3649,     // Use all 3649 requests
        maxDuration: '10m',   // Safety timeout
      },
    },
    thresholds: {
      http_req_duration: ['p(95)<5000'],  // 95% of requests should be under 5s
      http_req_failed: ['rate<0.05'],     // Error rate should be below 5%
    },
  };
  