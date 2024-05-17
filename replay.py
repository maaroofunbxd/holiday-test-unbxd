import json
import requests



with open("stratco_hodor.json", "r") as file:
    request_data = json.load(file)

new_hodor_api = "http://internal-ab9ffcb3f856f40a79c9c85d0fcf4098-37368537.ap-southeast-2.elb.amazonaws.com/sites/prod-stratco4681588782802/products/_filter"
old_hodor_api = "http://hodor.prod.ap-southeast-2.infra/sites/prod-stratco4681588782802/products/_filter"

def send_request(api_url, request_data):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(api_url, json=request_data, headers=headers)
    res = response.json()
    if response.status_code == 200:
        return res
    return "Status not ok"
    

def compare_responses(response1, response2):
    response1_products_sorted = sorted(response1.get("response", {}).get("products", []), key=lambda x: x["uniqueId"])
    response2_products_sorted = sorted(response2.get("response", {}).get("products", []), key=lambda x: x["uniqueId"])
    print("res sor",response1_products_sorted)
    print("res sor 2",response2_products_sorted)
    print("res1 count",response1["response"]["numberOfProducts"])
    print("res2 count",response2["response"]["numberOfProducts"])
    if response1_products_sorted == response2_products_sorted:
        return True
    else:
        return False

for request in request_data[:1]:
    if request["query_tag"] != "reranker":
        continue
    request["query"]["count"]= 50000
    resp_v2 = send_request(new_hodor_api, request["query"])
    resp_old = send_request(old_hodor_api, request["query"])
    if compare_responses(resp_v2, resp_old):
        print("Equal")
    else:
        print("NotEqual")

