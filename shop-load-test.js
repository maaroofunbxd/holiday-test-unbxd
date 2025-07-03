import http from 'k6/http';
import { SharedArray } from 'k6/data';

// const requests = new SharedArray('sample requests from production', function () {
//   return JSON.parse(open('/data/UShodorlogs.json'));
// });

export const options = {
  discardResponseBodies: false,
  scenarios: {
    contacts: {
      executor: 'ramping-arrival-rate',
      startRate: 5,
      timeUnit: '1s',
      preAllocatedVUs: 5,
      maxVUs: 5,
      stages: [
          { target: 5, duration: '1m' },
          { target: 10, duration: '1m' },
          { target: 5, duration: '1m' }
      ],
    },
  },
};


export default function () {
  const requestNo = Math.floor(Math.random() * 1000);

  //const request = requests[requestNo];
  const request = {"message": "Show me chairs"}

  const url = `http://hadron.prod.use-1d.infra/v1/sites/cityfurniture-com805331545375542/conversation/${requestNo}/chat?uid=1233`;

  const payload = JSON.stringify(request);

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  http.post(url, payload, params);
}
