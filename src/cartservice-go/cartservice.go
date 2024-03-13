package main

import (
	"context"
	"google.golang.org/grpc/codes"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/status"
	pb "hipstershop"
)

// CartService 提供了购物车服务
type CartService struct {
	store ICartStore
	pb.UnimplementedCartServiceServer
}

// NewCartService 创建一个新的购物车服务
func NewCartService(store ICartStore) *CartService {
	return &CartService{store: store}
}

func (s *CartService) AddItem(ctx context.Context, in *pb.AddItemRequest) (*pb.Empty, error) {
	err := s.store.AddItemAsync(in.UserId, in.Item.ProductId, in.Item.Quantity)
	if err != nil {
		return nil, err
	}
	return &pb.Empty{}, nil
}

func (s *CartService) EmptyCart(ctx context.Context, in *pb.EmptyCartRequest) (*pb.Empty, error) {
	err := s.store.EmptyCartAsync(in.UserId)
	if err != nil {
		return nil, err
	}
	return &pb.Empty{}, nil
}

func (s *CartService) GetCart(ctx context.Context, in *pb.GetCartRequest) (*pb.Cart, error) {
	return s.store.GetCartAsync(in.UserId)
}

func (s *CartService) Check(ctx context.Context, req *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{Status: healthpb.HealthCheckResponse_SERVING}, nil
}

func (s *CartService) Watch(req *healthpb.HealthCheckRequest, ws healthpb.Health_WatchServer) error {
	return status.Errorf(codes.Unimplemented, "health check via Watch not implemented")
}
