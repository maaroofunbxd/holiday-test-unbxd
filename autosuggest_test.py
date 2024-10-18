import pandas as pd
import requests
import json


csv_file_path = 'camperAsWingman.csv'
df = pd.read_csv(csv_file_path)

req  = 10
url = "https://search.unbxd.io" + df['msg'][0]
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
    if num_pro != num_pro_demo :
        print("res different for", url)



