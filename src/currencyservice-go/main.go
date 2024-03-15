package main

import (
	"encoding/json"
	"fmt"
	pb "hipstershop"
	"io/ioutil"
	"log"
	"math"
)

var currencyData map[string]string

// loadCurrencyData loads currency data from the JSON file.
func loadCurrencyData() {
	if currencyData != nil {
		return
	}

	data, err := ioutil.ReadFile("data/currency_conversion.json")
	if err != nil {
		log.Fatalf("Error reading currency data: %v", err)
	}

	if err := json.Unmarshal(data, &currencyData); err != nil {
		log.Fatalf("Error parsing currency data: %v", err)
	}
}

carry handles decimal/fractional carrying.
func carry(amount *pb.Money) *pb.Money {
	fractionSize := math.Pow(10, 9)
	amount.Nanos += int32(math.Mod(float64(amount.Units), 1) * fractionSize)
	amount.Units = int64(math.Floor(float64(amount.Units)) + math.Floor(float64(amount.Nanos)/fractionSize))
	amount.Nanos = int32(math.Mod(float64(amount.Nanos), fractionSize))
	return amount
}

func main() {
	loadCurrencyData()
	fmt.Printf("%v", currencyData)
}
