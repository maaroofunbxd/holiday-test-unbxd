import http from 'k6/http';
import { SharedArray } from 'k6/data';

const requests = new SharedArray('sample requests from production', function () {
  return JSON.parse(open('./data/reranker_request_recsv2_json_2.json'));
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
          { target: 120, duration: '3m' },
          { target: 150, duration: '3m' },
          { target: 100, duration: '2m' },
          { target: 75, duration: '3m' },
          { target: 40, duration: '3m' },
          { target: 30, duration: '2m' }
      ],
    },
  },
};


export default function () {
  const requestNo = Math.floor(Math.random() * requests.length);

  const request = requests[requestNo];

  const url = `http://internal-a30fe95f872334a299276a9530109ac0-1836140854.us-east-1.elb.amazonaws.com/v2.0/sites/${request.sitekey}/recommend`;
  
  const payload = JSON.stringify(request.query);

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  http.post(url, payload, params);
}