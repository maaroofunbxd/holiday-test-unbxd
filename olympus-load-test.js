import http from 'k6/http';
import { SharedArray } from 'k6/data';

const requests = new SharedArray('sample requests from production', function () {
  return JSON.parse(open('/data/olympus_data.json'));
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
          { target: 10, duration: '1m' },
          { target: 20, duration: '1m' },
          { target: 30, duration: '2m' },
          { target: 40, duration: '1m' },
          { target: 20, duration: '1m' },
          { target: 10, duration: '2m' }
      ],
    },
  },
};


export default function () {
  const requestNo = Math.floor(Math.random() * requests.length);
  const request = requests[requestNo];
  const url = `http://172.20.68.107/api/sites/pre-prod-ump13731624976343/feature_group/user_product/features?uid=${request}`;
  http.get(url);
}