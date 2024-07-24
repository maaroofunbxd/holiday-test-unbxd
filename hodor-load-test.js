import http from 'k6/http';
import { SharedArray } from 'k6/data';

const requests = new SharedArray('sample requests from production', function () {
  return JSON.parse(open('/data/us_angara_search_hodor_2.json'));
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

  const url = `http://internal-a7cd4c58d2f14497a95ab85e73fee6c5-227169144.us-east-1.elb.amazonaws.com/sites/${request.sitekey}/products/_filter?query_tag=${request.query_tag || "recommender"}`;
  // var url
  // if(request.query_tag == "recommender"){
  //   url = `http://34.86.235.188/sites/test_store_site/products/_detail`;
  // }else{
  //   url = `http://34.86.235.188/v2/sites/test_store_site/products/_filter`;
  // }
  
  const payload = JSON.stringify(request.query);

  const params = {
    headers: {
      'Content-Type': 'application/json',
    },
  };

  http.post(url, payload, params);
}