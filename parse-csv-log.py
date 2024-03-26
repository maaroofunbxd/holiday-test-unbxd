import pandas as pd
import json
import re
import random
from random import randrange


# csv_file_path = 'log_hodor_gcp_1.csv'
# csv_file_path_2 = 'log_hodor_gcp_2.csv'
# csv_file_path_3 = 'log_hodor_gcp_3.csv'
# csv_file_path_4 = 'log_hodor_gcp_4.csv'
# csv_file_path_5 = 'log_hodor_gcp_5.csv'
# text_file_path = "hodor_request_2.txt"
# df1 = pd.read_csv(csv_file_path)
# df2 = pd.read_csv(csv_file_path_2)
# df3 = pd.read_csv(csv_file_path_3)
# df4 = pd.read_csv(csv_file_path_4)
# df5 = pd.read_csv(csv_file_path_5)

# df = pd.concat([df1, df2, df3, df4, df5], ignore_index=True)

# extracted_column = df['log']

# jeromes_uid = pd.read_csv("jeromes_uids.csv")

# stopbed_uids = pd.read_csv("generated_uids_gcp.csv")

# with open('fake-use-requests-reranker-7k.json') as json_file:
#     json_data = json.load(json_file)

# miniature_uids = []
# for data in json_data:
#     if data["sitekey"] == "prod-miniaturemarket-com811741582229555":
#         miniature_uids.append(data["userId"])



# output_entries = []
# output_entries.append("[")
# for entry in df['log']:
#     if "query received" in entry:
#         # Use regular expression to extract relevant information
#         match = re.search(r'query received\s+(.*)', entry)
#         if match:
#             query_data = json.loads(match.group(1))
#             query_data['query']['count'] = 36
#             query_data['query']['deviceType'] = "UNKNOWN"
#             query_data['query']['norm'] = 40
#             query_data['query']['platform'] = "netcore"
#             query_data['query']['algo'] = "vav"
#             query_data['query']['algoVersion'] = "v2"
#             query_data['query']['userId'] = stopbed_uids["UID"].sample(n=1).tolist()[0]
#             query_data['query']['pids'] = []
#             query_data['query']['sitekey'] = query_data["sitekey"]
#             if query_data["sitekey"] == "prod-jeromes-us812431587636548":
#                 query_data["query"]["userId"] = jeromes_uid["user_id"].sample(n=1).tolist()[0]
#             if query_data["sitekey"] == "prod-miniaturemarket-com811741582229555":
#                 query_data["query"]["userId"] = random.choice(miniature_uids)
#             try:
#                 #print(query_data['query']['filters']['componentFilters_1']['component_filters'][0]['group'])
#                 query_data['query']['filters']['componentFilters_2']['component_filters'][0]['group'] = 2
#                 query_data['query']['filters']['componentFilters_1']['component_filters'][0]['group'] = 2
#             except Exception as e:
#                 pass
#             if query_data["query_tag"] == "reranker":
#                 stdata = json.dumps(query_data)
#                 output_entries.append(stdata+",")

# output_entries[-1] = output_entries[-1][:-1]
# output_entries.append("]")

# with open('reranker_request_recsv2_gcp_json_2.json', 'w') as file:
#     file.write('\n'.join(output_entries))


f = open('hodor_request_gcp_json_2.json')
data = json.load(f)
print(data[0]["query_tag"])

new_req = []
for x in data:
    if x["query_tag"] == "recommender":
        pro = []
        l = len(x["query"]["products"])
        for i in range(100):
            rr = randrange(l)
            pro.append(x["query"]["products"][rr])
        x["query"]["products"] = pro
        new_req.append(x)



with open('hodor_request_gcp_json_recommender_2.json', 'w') as file:
    json.dump(new_req, file, indent=4)