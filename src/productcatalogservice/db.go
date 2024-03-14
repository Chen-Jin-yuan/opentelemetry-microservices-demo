package main

import (
	"encoding/json"
	"gopkg.in/mgo.v2/bson"
	"os"

	"gopkg.in/mgo.v2"
)

type Money struct {
	CurrencyCode string `json:"currency_code" bson:"currency_code"`
	Units        int64  `json:"units" bson:"units"`
	Nanos        int32  `json:"nanos" bson:"nanos"`
}

type Product struct {
	Id          string   `json:"id" bson:"id"`
	Name        string   `json:"name" bson:"name"`
	Description string   `json:"description" bson:"description"`
	Picture     string   `json:"picture" bson:"picture"`
	PriceUsd    *Money   `json:"priceUsd" bson:"price_usd"`
	Categories  []string `json:"categories" bson:"categories"`
}

func initializeDatabase() {
	// 读取product.json文件
	file, err := os.Open("products.json")
	if err != nil {
		log.Fatalf("Error opening product.json file: %v", err)
	}
	defer file.Close()

	// 解码JSON数据
	var data map[string][]Product
	err = json.NewDecoder(file).Decode(&data)
	if err != nil {
		log.Fatalf("Error decoding JSON: %v", err)
	}

	// 设置MongoDB连接字符串
	mongoURI := os.Getenv("MONGO_URI")
	if mongoURI == "" {
		log.Fatal("MONGO_URI environment variable is not set")
	}

	// 创建MongoDB会话
	session, err := mgo.Dial(mongoURI)
	if err != nil {
		log.Fatalf("Error creating MongoDB session: %v", err)
	}

	// 选择数据库和集合
	db := session.DB("productcatalogservice-db")
	collection = db.C("products")

	// 插入数据到MongoDB
	for _, product := range data["products"] {
		// 检查是否已存在相同的Id
		count, err := collection.Find(bson.M{"id": product.Id}).Count()
		if err != nil {
			log.Printf("Error checking for existing product %s: %v", product.Id, err)
			continue
		}
		if count > 0 {
			log.Printf("Product %s already exists, skipping insertion", product.Id)
			continue
		}

		// 插入新产品
		err = collection.Insert(product)
		if err != nil {
			log.Printf("Error inserting product %s: %v", product.Id, err)
		} else {
			log.Printf("Product %s inserted successfully", product.Id)
		}
	}
}
