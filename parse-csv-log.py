import pandas as pd
import json
import re
csv_file_path = 'log_hodor_gcp_1.csv'
csv_file_path_2 = 'log_hodor_gcp_2.csv'
csv_file_path_3 = 'log_hodor_gcp_3.csv'
csv_file_path_4 = 'log_hodor_gcp_4.csv'
csv_file_path_5 = 'log_hodor_gcp_5.csv'
text_file_path = "hodor_request_2.txt"
df1 = pd.read_csv(csv_file_path)
df2 = pd.read_csv(csv_file_path_2)
df3 = pd.read_csv(csv_file_path_3)
df4 = pd.read_csv(csv_file_path_4)
df5 = pd.read_csv(csv_file_path_5)

df = pd.concat([df1, df2, df3, df4, df5], ignore_index=True)

extracted_column = df['log']

# extracted_column.to_csv(text_file_path, index=False, header=False)

output_entries = []
output_entries.append("[")
for entry in df['log']:
    if "query received" in entry:
        # Use regular expression to extract relevant information
        match = re.search(r'query received\s+(.*)', entry)
        if match:
            query_data = json.loads(match.group(1))
            query_data['query']['count'] = 9999
            # try:
            #     #print(query_data['query']['filters']['componentFilters_1']['component_filters'][0]['group'])
            #     #query_data['query']['filters']['componentFilters_1']['component_filters'][0]['group'] = 2
            #     #del query_data['query']["filters"]["componentFilters_2"]
            # except Exception as e:
            #     pass
            stdata = json.dumps(query_data)
            output_entries.append(stdata+",")

output_entries[-1] = output_entries[-1][:-1]
output_entries.append("]")

with open('hodor_request_gcp_json_2.json', 'w') as file:
    file.write('\n'.join(output_entries))
