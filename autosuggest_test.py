import pandas as pd
import requests
import json


csv_file_path = 'camperAsWingman.csv'
df = pd.read_csv(csv_file_path)

req  = 10
# url = "https://search.unbxd.io" + df['msg'][0]

# res = requests.get(url)
# jres = json.loads(res.content)
# prod_array =  jres.get('response').get('products')
# print(prod_array[0].get('autosuggest'))

for i in range(0,req):
    url = "https://search.unbxd.io" + df['msg'][i]
    demo_url = "http://internal-a0484b72775f611ed98b10284fd5d35d-2106550818.eu-west-2.elb.amazonaws.com"+ df['msg'][i]
    res = requests.get(url)
    demo_res = requests.get(demo_url)
    jres = json.loads(res.content)
    jres_demo = json.loads(demo_res.content)  
    num_pro = jres.get('response').get('numberOfProducts')
    num_pro_demo = jres_demo.get('response').get('numberOfProducts')
    print(f"num_pro {num_pro} num_pro_demo {num_pro_demo}")
    prod_array =  jres.get('response').get('products')
    pro_array_demo = jres_demo.get('response').get('products')
    if num_pro != num_pro_demo :
        print("res different for", url)
    if len(prod_array) != len(pro_array_demo):
        print("len prod array is different for url", url)
        continue
    for i in range(0, len(prod_array)):
        if prod_array[i].get("autosuggest") != pro_array_demo[i].get("autosuggest"):
            print("autosuggest is different for url", url)
            break




