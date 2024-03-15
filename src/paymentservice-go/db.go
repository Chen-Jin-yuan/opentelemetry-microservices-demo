package main

import (
	"gopkg.in/mgo.v2"
	"os"
	"time"
)

var collection *mgo.Collection

type Money struct {
	CurrencyCode string `json:"currencyCode" bson:"currencyCode"`
	Units        int64  `json:"units" bson:"units"`
	Nanos        int32  `json:"nanos" bson:"nanos"`
}

type Transaction struct {
	CreditCardNumber          string    `bson:"credit_card_number"`
	CreditCardType            string    `bson:"credit_card_type"`
	CreditCardExpirationYear  int32     `bson:"credit_card_expiration_year"`
	CreditCardExpirationMonth int32     `bson:"credit_card_expiration_month"`
	TransactionID             string    `bson:"transaction_id"`
	TransactionAmount         *Money    `bson:"transaction_amount"`
	Timestamp                 time.Time `bson:"timestamp"`
}

func initializeDatabase() {
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
	db := session.DB("paymentservice-db")
	collection = db.C("payment")
}

// Function to read data from MongoDB and print
func readAndPrintDataFromDB() error {
	// Query the data
	var transactions []Transaction
	err := collection.Find(nil).All(&transactions)
	if err != nil {
		log.Printf("Error reading data from MongoDB: %v", err)
		return err
	}

	// Print the data
	log.Println("Data read from MongoDB:")
	for _, transaction := range transactions {
		log.Printf("Transaction ID: %s", transaction.TransactionID)
		log.Printf("Credit Card Number: %s", transaction.CreditCardNumber)
		log.Printf("Credit Card Type: %s", transaction.CreditCardType)
		log.Printf("Credit Card Expiration Year: %d", transaction.CreditCardExpirationYear)
		log.Printf("Credit Card Expiration Month: %d", transaction.CreditCardExpirationMonth)
		log.Printf("Transaction Amount: %d %s", transaction.TransactionAmount.Units, transaction.TransactionAmount.CurrencyCode)
		log.Printf("Timestamp: %s", transaction.Timestamp)
		log.Println("-------------------------------------------")
	}

	return nil
}
