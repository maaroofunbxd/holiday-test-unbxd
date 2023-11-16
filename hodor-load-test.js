import http from 'k6/http';
import { SharedArray } from 'k6/data';

const requests = new SharedArray('sample requests from production', function () {
  return JSON.parse(open('./data/hodor_request_json_2.json'));
});


export const options = {
  discardResponseBodies: true,
  scenarios: {
    contacts: {
      executor: 'ramping-arrival-rate',
      startRate: 15,
      timeUnit: '1s',
      preAllocatedVUs: 10,
      maxVUs: 20,
      stages: [
          { target: 20, duration: '2m' },
          { target: 25, duration: '5m' },
          { target: 30, duration: '5m' },
        //   { target: 35, duration: '2m' },
        //   { target: 60, duration: '1m' },
        //   { target: 100, duration: '2m' },
        //   { target: 60, duration: '2m' },
        //   { target: 50, duration: '3m' },
        //   { target: 40, duration: '3m' },
        //   { target: 30, duration: '2m' }
      ],
    },
  },
};


export default function () {
  const requestNo = Math.floor(Math.random() * requests.length);

  const request = requests[requestNo];

  const url = `http://internal-a36537a6c186e48569dab402d141c9e9-2103372624.us-east-1.elb.amazonaws.com/sites/${request.sitekey}/products/_filter?query_tag=${request.query_tag || "recommender"}`;

  const payload = JSON.stringify(request.query);

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Host': 'hodor-sharded.dev-gcp.infra',
    },
  };

  http.post(url, payload, params);
}