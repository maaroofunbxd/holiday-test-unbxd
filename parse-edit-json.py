import json
import random

# # Load the structure JSON
# with open('us_angara_search_hodor.json', 'r') as file:
#     structure_data = json.load(file)

# # Load the products JSON
# with open('us_anagara_pids.json', 'r') as file:
#     products_data_1 = json.load(file)

# products_data = [{"id": product_id} for product_id in products_data_1]

# # Number of products to randomly select
# num_products = 25

# # Select random products
# selected_products = random.sample(products_data, num_products)

# # Update the products field in the structure JSON
# for entry in structure_data:
#     if 'query' in entry and 'products' in entry['query']:
#         entry['query']['products'] = selected_products

# # Save the updated structure JSON
# with open('us_angara_search_hodor_2.json', 'w') as file:
#     json.dump(structure_data, file, indent=4)

# print("Updated structure.json with random products")

f = open('express_products4.json')
productsAll = json.load(f)

# num_products = 25

import json
import random


# Function to generate random product data
def generate_random_product_data(num_products=25):
    products =[]
    selected_products = random.sample(productsAll, num_products)
    for y in selected_products:
        product_id = y["uniqueId"]
        variants = []
        for x in y["variants"]:
            variants.append({"id":x["variantId"]})
        products.append({
            "id": product_id,
            "variants": variants[:5]
        })
    return {"products": products, "include_variants": True}

# Generate random product data
total_request = 1000
random_product_quries = []
for i in range(0,total_request):
    random_product_data = generate_random_product_data(num_products=25)
    random_product_quries.append(random_product_data)

# Convert to JSON and save to a file
json_file_path = 'express_queries.json'
with open(json_file_path, 'w') as json_file:
    json.dump(random_product_quries, json_file, indent=3)

print(f"Random product data saved to {json_file_path}")
