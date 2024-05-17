import json
import requests



with open("mwave_hodor.json", "r") as file:
    request_data = json.load(file)

new_hodor_api = "http://internal-ab9ffcb3f856f40a79c9c85d0fcf4098-37368537.ap-southeast-2.elb.amazonaws.com/sites/ss-unbxd-prod-mwave43601693203163/products/_filter"
old_hodor_api = "http://hodor.prod.ap-southeast-2.infra/sites/ss-unbxd-prod-mwave43601693203163/products/_filter"

def send_request(api_url, request_data):
    headers = {'Content-Type': 'application/json'}
    response = requests.post(api_url, json=request_data, headers=headers)
    res = response.json()
    return res
    

def compare_responses(response1, response2):
    if response1 == response2:
        return True
    else:
        return False

for request in request_data[:1]:
    resp_v2 = send_request(new_hodor_api, request["query"])
    resp_old = send_request(old_hodor_api, request["query"])
    print("resp_v2",resp_v2)
    print("resp_old", resp_old)
    if compare_responses(resp_v2, resp_old):
        print("Eqaul")
    else:
        print("NotEqual")

