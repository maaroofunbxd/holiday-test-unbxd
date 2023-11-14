import re

input_file_path = 'hodor_request.txt'

with open(input_file_path, 'r') as file:
    log_entries = file.read()

entries = log_entries.split('\n')

# Extract information after "query received"
output_entries = []
for entry in entries:
    if "query received" in entry:
        # Use regular expression to extract relevant information
        match = re.search(r'query received\s+(.*)', entry)
        if match:
            output_entries.append(match.group(1)+",")

# Write output back to the same file
with open('hodor_request_json.json', 'w') as file:
    file.write('\n'.join(output_entries))