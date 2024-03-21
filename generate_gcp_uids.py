import csv

base_uid = "uid-1700288867788-138"
base_uid2 = "uid-1700252382820-14"
uids = []

for i in range(100):
    current_uid = base_uid + str(i).zfill(2)
    uids.append(current_uid)

for i in range(100):
    current_uid = base_uid2 + str(i).zfill(2)
    uids.append(current_uid)

# Write uids to a CSV file
csv_file_path = "generated_uids_gcp.csv"

with open(csv_file_path, 'w', newline='') as csv_file:
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["UID"])  # Write header

    for uid in uids:
        csv_writer.writerow([uid])