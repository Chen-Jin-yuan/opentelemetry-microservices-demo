package main

import (
	"context"
	"errors"
	"fmt"
	"github.com/redis/go-redis/v9"
	"google.golang.org/protobuf/proto"
	pb "hipstershop"
	"sync"
)

// RedisCartStore 实现了使用 Redis 作为后端存储的购物车存储。
type RedisCartStore struct {
	CART_FIELD_NAME         string
	REDIS_RETRY_NUM         int
	redis                   *redis.Client
	isRedisConnectionOpened bool
	locker                  sync.Mutex
	emptyCartBytes          []byte
}

// NewRedisCartStore 创建一个 RedisCartStore 实例。
func NewRedisCartStore(redisAddress string) *RedisCartStore {
	// Serialize empty cart into byte array.
	cart := &pb.Cart{}
	emptyCartBytes, _ := proto.Marshal(cart)

	rdb := redis.NewClient(&redis.Options{
		Addr:     redisAddress,
		Password: "", // no password set
		DB:       0,  // use default DB
	})

	return &RedisCartStore{
		CART_FIELD_NAME:         "cart",
		REDIS_RETRY_NUM:         30,
		redis:                   rdb,
		isRedisConnectionOpened: false,
		emptyCartBytes:          emptyCartBytes,
	}
}

// InitializeAsync 初始化 RedisCartStore。
func (r *RedisCartStore) InitializeAsync() error {
	r.ensureRedisConnected()
	return nil
}

// AddItemAsync 将商品添加到购物车。
func (r *RedisCartStore) AddItemAsync(userId, productId string, quantity int32) error {
	r.ensureRedisConnected()

	ctx := context.Background()

	value, err := r.redis.HGet(ctx, userId, r.CART_FIELD_NAME).Bytes()
	if err != nil && !errors.Is(err, redis.Nil) {
		return fmt.Errorf("failed to access cart storage: %w", err)
	}

	cart := &pb.Cart{}
	if err := proto.Unmarshal(value, cart); err != nil && !errors.Is(err, redis.Nil) {
		return fmt.Errorf("failed to unmarshal cart data: %w", err)
	}

	if cart == nil {
		cart = &pb.Cart{
			UserId: userId,
			Items:  make([]*pb.CartItem, 0),
		}
	}

	var existingItem *pb.CartItem
	for _, item := range cart.Items {
		if item.ProductId == productId {
			existingItem = item
			break
		}
	}

	if existingItem == nil {
		newItem := &pb.CartItem{
			ProductId: productId,
			Quantity:  int32(quantity),
		}
		cart.Items = append(cart.Items, newItem)
	} else {
		existingItem.Quantity += int32(quantity)
	}

	cartBytes, _ := proto.Marshal(cart)
	err = r.redis.HSet(ctx, userId, r.CART_FIELD_NAME, cartBytes).Err()
	if err != nil {
		return fmt.Errorf("failed to update cart in storage: %w", err)
	}

	return nil
}

// EmptyCartAsync 清空购物车。
func (r *RedisCartStore) EmptyCartAsync(userId string) error {
	r.ensureRedisConnected()

	ctx := context.Background()

	err := r.redis.HSet(ctx, userId, r.CART_FIELD_NAME, r.emptyCartBytes).Err()
	if err != nil {
		return fmt.Errorf("failed to empty cart in storage: %w", err)
	}

	return nil
}

// GetCartAsync 获取用户的购物车。
func (r *RedisCartStore) GetCartAsync(userId string) (*pb.Cart, error) {
	r.ensureRedisConnected()

	ctx := context.Background()

	value, err := r.redis.HGet(ctx, userId, r.CART_FIELD_NAME).Bytes()
	if err != nil && !errors.Is(err, redis.Nil) {
		return nil, fmt.Errorf("failed to access cart storage: %w", err)
	}

	cart := &pb.Cart{}
	if err := proto.Unmarshal(value, cart); err != nil && !errors.Is(err, redis.Nil) {
		return nil, fmt.Errorf("failed to unmarshal cart data: %w", err)
	}

	if cart == nil {
		cart = &pb.Cart{
			UserId: userId,
			Items:  make([]*pb.CartItem, 0),
		}
	}

	return cart, nil
}

// Ping 检查与 Redis 的连接状态。
func (r *RedisCartStore) Ping() bool {
	ctx := context.Background()
	_, err := r.redis.Ping(ctx).Result()
	return err == nil
}

// ensureRedisConnected 确保与 Redis 的连接已建立。
func (r *RedisCartStore) ensureRedisConnected() {
	r.locker.Lock()
	defer r.locker.Unlock()

	if !r.isRedisConnectionOpened {
		ctx := context.Background()
		_, err := r.redis.Ping(ctx).Result()
		if err != nil {
			panic(fmt.Errorf("failed to connect to Redis: %w", err))
		}
		r.isRedisConnectionOpened = true
	}
}
