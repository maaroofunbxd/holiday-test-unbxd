import json
import random

# Function to generate random JSON objects

fields = {
    "fields": [
        "uniqueId",
        "s_p_color",
        "pattern",
        "imageUrl",
        "colorName",
        "description",
        "color",
        "productImage",
        "newProduct",
        "size",
        "s_p_size",
        "s_p_availability",
        "s_p_selling_price",
    ],
    "store_fields": ["name", "location", "storeId"],
}


def generate_json():
    products = []
    for _ in range(100):
        product_id = random.randint(1, 19400)
        stores = []
        for _ in range(5):
            store_id = random.randint(1, 500)
            stores.append({"id": str(store_id)})
        product = {"id": str(product_id), "stores": stores}
        products.append(product)
        mergedJson = {"include_variants": False, "products": products}
        mergedJson.update(fields)
    return {"query_tag": "recommender", "query": mergedJson}


json_data = [generate_json() for _ in range(2000)]


with open("store_reuest.json", "w") as file:
    json.dump(json_data, file)
