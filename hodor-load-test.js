import http from 'k6/http';
import { SharedArray } from 'k6/data';

const requests = new SharedArray('sample requests from production', function () {
  return JSON.parse(open('/data/express_queries.json'));
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
          { target: 70, duration: '1m' },
          { target: 100, duration: '2m' },
          { target: 150, duration: '2m' },
          { target: 150, duration: '2m' },
          { target: 250, duration: '3m' },
          { target: 250, duration: '1m' },
          { target: 200, duration: '2m' },
          { target: 100, duration: '2m' },
          { target: 70, duration: '1m' }
      ],
    },
  },
};


export default function () {
  const requestNo = Math.floor(Math.random() * requests.length);

  const request = requests[requestNo];

  const url = `http://internal-a7cd4c58d2f14497a95ab85e73fee6c5-227169144.us-east-1.elb.amazonaws.com/sites/test-unbxd_213213/products/_filter`;
  // var url
  // if(request.query_tag == "recommender"){
  //   url = `http://34.86.235.188/sites/test_store_site/products/_detail`;
  // }else{
  //   url = `http://34.86.235.188/v2/sites/test_store_site/products/_filter`;
  // }
  
  const payload = JSON.stringify(request);

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  http.post(url, payload, params);
}