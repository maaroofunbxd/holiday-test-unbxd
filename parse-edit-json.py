import json
import random

# Load the structure JSON
with open('us_angara_search_hodor.json', 'r') as file:
    structure_data = json.load(file)

# Load the products JSON
with open('us_anagara_pids.json', 'r') as file:
    products_data_1 = json.load(file)

products_data = [{"id": product_id} for product_id in products_data_1]

# Number of products to randomly select
num_products = 25

# Select random products
selected_products = random.sample(products_data, num_products)

# Update the products field in the structure JSON
for entry in structure_data:
    if 'query' in entry and 'products' in entry['query']:
        entry['query']['products'] = selected_products

# Save the updated structure JSON
with open('us_angara_search_hodor_2.json', 'w') as file:
    json.dump(structure_data, file, indent=4)

print("Updated structure.json with random products")
