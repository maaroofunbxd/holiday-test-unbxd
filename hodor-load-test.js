import http from 'k6/http';
import { SharedArray } from 'k6/data';

const requests = new SharedArray('sample requests from production', function () {
  return JSON.parse(open('./data/hodor_request_json_2.json'));
});


export const options = {
  discardResponseBodies: false,
  scenarios: {
    contacts: {
      executor: 'ramping-arrival-rate',
      startRate: 15,
      timeUnit: '1s',
      preAllocatedVUs: 10,
      maxVUs: 20,
      stages: [
          { target: 40, duration: '1m' },
          { target: 75, duration: '2m' },
          { target: 100, duration: '3m' },
          { target: 120, duration: '2m' },
          { target: 100, duration: '2m' },
          { target: 40, duration: '2m' },
        //   { target: 20, duration: '3m' },
        //   { target: 40, duration: '3m' },
        //   { target: 30, duration: '2m' }
      ],
    },
  },
};


export default function () {
  const requestNo = Math.floor(Math.random() * requests.length);

  const request = requests[requestNo];

  const url = `http://internal-abdf0d577ca5d487cb684e1b7ce2f60b-168170469.us-east-1.elb.amazonaws.com/sites/${request.sitekey}/products/_filter?query_tag=${request.query_tag || "recommender"}`;

  const payload = JSON.stringify(request.query);

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Host': 'hodor-sharded.dev-gcp.infra',
    },
  };

  http.post(url, payload, params);
}