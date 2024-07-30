import http from 'k6/http';
import { SharedArray } from 'k6/data';

const products = new SharedArray('products', function() {
    return JSON.parse(open('/data/express_products4.json')); // Load JSON data from file
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
          { target: 60, duration: '2m' },
          { target: 70, duration: '2m' },
          { target: 80, duration: '2m' },
          { target: 80, duration: '1m' },
          { target: 100, duration: '2m' },
          { target: 60, duration: '2m' },
          { target: 30, duration: '2m' },
      ],
    },
  },
};

function shuffle(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
}


export default function () {
    const requestNo = Math.floor(Math.random() * products.length);
    const request = products[requestNo];
    const productsUrl = 'http://internal-a7cd4c58d2f14497a95ab85e73fee6c5-227169144.us-east-1.elb.amazonaws.com/sites/test-unbxd_213213/products/_insertbatch?isfilter=false';
    // let mutableProducts = Array.from(products);
    // shuffle(mutableProducts);
    // const selectedProducts = products.slice(0, numProducts);
    http.post(productsUrl, JSON.stringify(request), {
        headers: { 'Content-Type': 'application/json' },
    });
}