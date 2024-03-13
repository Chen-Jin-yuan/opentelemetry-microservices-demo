package main

import (
	pb "hipstershop"
)

// ICartStore 定义了购物车存储接口
type ICartStore interface {
	InitializeAsync() error
	AddItemAsync(userId, productId string, quantity int32) error
	EmptyCartAsync(userId string) error
	GetCartAsync(userId string) (*pb.Cart, error)
}
