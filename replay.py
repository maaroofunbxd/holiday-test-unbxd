import requests
import json


with open("us_angara_hodor.json", "r") as file:
    request_data = json.load(file)

new_hodor_api = "http://internal-a7cd4c58d2f14497a95ab85e73fee6c5-227169144.us-east-1.elb.amazonaws.com/sites/ss-unbxd-Prod-Angara-US809761688720875/products/_filter"
old_hodor_api = "http://hodor.prod.eu-west-2.infra/sites/ss-unbxd-prod-alohassandles-shopifyplus43721687326386/products/_filter"

def send_request(api_url, request_data):
    headers = {'Content-Type': 'application/json'}
    try:
        response = requests.post(api_url, json=request_data, headers=headers)
        res = response.json()
        if len(res["response"]["products"]) == 0:
            print("Empty res")
        if response.status_code == 200:
            return "OK"
    except Exception as e:
        return "NOTOK"
    
    return "NOTOK"

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

for request in request_data:
    # if request["query_tag"] != "reranker":
    #     continue
    #request["query"]["count"]= 50000
    resp_v2 = send_request(new_hodor_api, request["query"])
    if resp_v2 == "NOTOK":
        print(resp_v2)
        print(request["query"])
    #resp_old = send_request(old_hodor_api, request["query"])
    # if compare_responses(resp_v2, resp_old):
    #     print("Equal")
    # else:
    #     print("NotEqual")