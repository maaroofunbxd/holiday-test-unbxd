import pandas as pd
import json
import re
import random
from random import randrange


csv_file_path = 'motor.csv'
# csv_file_path_2 = 'log_hodor_gcp_2.csv'
# csv_file_path_3 = 'log_hodor_gcp_3.csv'
# csv_file_path_4 = 'log_hodor_gcp_4.csv'
# csv_file_path_5 = 'log_hodor_gcp_5.csv'
# text_file_path = "hodor_request_2.txt"
df = pd.read_csv(csv_file_path)
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



output_entries = []
output_entries.append("[")
for entry in df['log']:
    if "query received" in entry:
        # Use regular expression to extract relevant information
        match = re.search(r'query received\s+(.*)', entry)
        if match:
            query_data = json.loads(match.group(1))
            stdata = json.dumps(query_data)
            output_entries.append(stdata+",")

output_entries[-1] = output_entries[-1][:-1]
output_entries.append("]")

with open('gcp_motor_hodor.json', 'w') as file:
    file.write('\n'.join(output_entries))


# f = open('hodor_request_gcp_json_2.json')
# data = json.load(f)
# print(data[0]["query_tag"])

# new_fields = []
# for i in range(80):
#     field_name = f"field_{i+1}"
#     new_fields.append(field_name)

# print(new_fields)

# new_req = []
# for x in data:
#     if x["query_tag"] == "recommender":
#         pro = []
#         l = len(x["query"]["products"])
#         for i in range(100):
#             rr = randrange(l)
#             pro.append(x["query"]["products"][rr])
#         x["query"]["products"] = pro
#         # x["query"]["fields"].extend(new_fields)
#         x["query"]["fields"] = ["all_fields"]
#         new_req.append(x)
       



# with open('hodor_request_gcp_json_recommender_all_fields_2.json', 'w') as file:
#     json.dump(new_req, file, indent=4)