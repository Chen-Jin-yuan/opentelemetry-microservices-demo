import json
import random
import string
import os




class Money:
    def __init__(self, currencyCode, units, nanos):
        self.currencyCode = currencyCode
        self.units = units
        self.nanos = nanos

class Product:
    def __init__(self, id, name, description, picture, priceUsd, categories):
        self.id = id
        self.name = name
        self.description = description
        self.picture = picture
        self.priceUsd = priceUsd
        self.categories = categories

def generate_random_string(length):
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_random_products(num):
    products = []
    for i in range(num):
        product = Product(
            id=f"{generate_random_string(10)}",
            name=f"Product {i+1}",
            description=f"Description of Product {i+1}",
            picture=f"/static/img/products/product-{i+1}.jpg",
            priceUsd=Money("USD", random.randint(1, 100), random.randint(0, 999999999)),
            categories=["category1", "category2"]
        )
        products.append(product.__dict__)
    return {"products": products}

def money_to_dict(obj):
    return {"currencyCode": obj.currencyCode, "units": obj.units, "nanos": obj.nanos}

def main():
    num_products = 191
    products_data = generate_random_products(num_products)

    # Convert Money objects to dictionaries
    for product in products_data["products"]:
        product["priceUsd"] = money_to_dict(product["priceUsd"])

    with open("products.json", "w") as file:
        json.dump(products_data, file, indent=4)

    print("Products data generated and saved to products.json")

if __name__ == "__main__":
    # main()
    # 获取文件路径
    file_path = "products.json"

    # 获取文件大小（以字节为单位）
    file_size = os.path.getsize(file_path)

    print(f"JSON 文件转换为二进制的大小为: {file_size} 字节")
