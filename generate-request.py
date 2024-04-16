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
    "store_fields": ["storeId"],
    "variant_fields":["s_v_redline","s_v_storeAvailability","variantId","v_color","v_colorCode","s_v_displayable"],
}

## 135561
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

def generate_json_with_variants():
    products = []
    for _ in range(100):
        product_id = random.randint(1, 19400)
        variants = []
        for _ in range(10):
            variant_id = random.randint(1, 135561)
            stores = []
            for _ in range(5):
                store_id = random.randint(1000000, 1000500)
                stores.append({"id": str(store_id)})
            variant = {"id": str(variant_id), "stores": stores}
            variants.append(variant)
        product = {"id": str(product_id), "variants": variants}
        products.append(product)
        mergedJson = {"include_variants": True, "products": products}
        mergedJson.update(fields)
    return {"query_tag": "recommender", "query": mergedJson}

json_data = [generate_json_with_variants() for _ in range(2000)]


with open("store_request_variants.json", "w") as file:
    json.dump(json_data, file)


# base_request = {
#     "fields": ["uniqueId"],
#     "store_specific_filters": {
#         "products": {
#             "componentFilters_1": {
#                 "component_filters": [
#                     {
#                         "field_name": "s_p_availability",
#                         "values": ["True"],
#                         "condition": 1,
#                         "type": 1,
#                         "group": 1
#                     },
#                     {
#                         "field_name": "s_p_color",
#                         "values": ["White"],
#                         "condition": 1,
#                         "type": 1,
#                         "group": 1
#                     }
#                 ]
#             }
#         }
#     },
#     "filters": {
#         "componentFilters_1": {
#             "component_filters": [
#                 {
#                     "field_name": "color",
#                     "values": ["Blue", "Red"],
#                     "condition": 1,
#                     "type": 1,
#                     "group": 2
#                 }
#             ]
#         }
#     },
#     "stores_filters": {
#         "componentFilters_1": {
#             "component_filters": [
#                 {
#                     "field_name": "storeId",
#                     "values": ["363", "1"],
#                     "condition": 1,
#                     "type": 1,
#                     "group": 1
#                 }
#             ]
#         }
#     },
#     "include_variants": False,
#     "count": 5000
# }

# requests = []
# uniqueColor = ["Multi-Color", "Black", "Blue", "Brown", "Neutral", "White", "Pink", "Green", "Gold", "Purple", "Gray", "Red", "Orange", "Default", "Yellow", "Silver", "Light Pink"]
# for j in range(2000):
#     request = base_request.copy()
    
#     request["store_specific_filters"]["products"]["componentFilters_1"]["component_filters"][0]["values"] = [random.choice(["True", "False"])]
#     request["store_specific_filters"]["products"]["componentFilters_1"]["component_filters"][0]["condition"] = random.randint(1,2)
#     r1 = random.randint(1, 3)
#     if j%2 == 0:
#         r1 = 1
#     request["store_specific_filters"]["products"]["componentFilters_1"]["component_filters"][1]["values"] = random.sample(uniqueColor, r1)
#     r2 = random.randint(1, 3)
#     if j%2 == 0:
#         r2 = 1
#     request["filters"]["componentFilters_1"]["component_filters"][0]["values"] = random.sample(uniqueColor, r2)
#     request["filters"]["componentFilters_1"]["component_filters"][0]["condition"] = random.randint(1,2)
#     stores = []
#     r3 = random.randint(1, 10)
#     for _ in range(r3):
#         store_id = random.randint(1, 500)
#         stores.append(str(store_id))
#     request["stores_filters"]["componentFilters_1"]["component_filters"][0]["values"] = stores
#     requests.append({"query_tag": "reranker", "query": request})

# with open("postgres_store_request.json", "w") as file:
#     json.dump(requests, file)