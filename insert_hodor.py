import json
import requests

products = []

with open('express_products4.json') as file:
    json.dump(products,file)


productsUrl = "http://internal-a7cd4c58d2f14497a95ab85e73fee6c5-227169144.us-east-1.elb.amazonaws.com/sites/test-unbxd_213213/products/_insertbatch?isfilter=false"

headers = {'Content-Type': 'application/json'}
batch_size = 3000
for i in range(0, len(products), batch_size):
    batch = products[i:i + batch_size]
    response = requests.post(productsUrl, json=batch, headers=headers)
    print("Status Code for product insert", response.status_code)
