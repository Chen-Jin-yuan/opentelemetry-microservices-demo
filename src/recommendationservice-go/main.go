package main

import (
	"context"
	"fmt"
	"github.com/Chen-Jin-yuan/grpc/consul"
	"github.com/google/uuid"
	"github.com/grpc-ecosystem/grpc-opentracing/go/otgrpc"
	"github.com/opentracing/opentracing-go"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc/keepalive"
	"math/rand"
	"net"
	"os"
	"strconv"
	"time"
	"tracing"

	"google.golang.org/grpc"

	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	pb "hipstershop"
)

const (
	name       = "recommendationservice"
	consulAddr = "consul:8500"
	jaegerAddr = "jaeger:6831"
)

var (
	log      *logrus.Logger
	registry *consul.Client
	Tracer   opentracing.Tracer
)

func init() {
	log = logrus.New()
	log.Level = logrus.DebugLevel
	log.Formatter = &logrus.JSONFormatter{
		FieldMap: logrus.FieldMap{
			logrus.FieldKeyTime:  "timestamp",
			logrus.FieldKeyLevel: "severity",
			logrus.FieldKeyMsg:   "message",
		},
		TimestampFormat: time.RFC3339Nano,
	}
	log.Out = os.Stdout

	var err error
	// recommend service
	Tracer, err = tracing.Init("recommendationservice", jaegerAddr)
	if err != nil {
		log.Errorf("Got error while initializing jaeger agent: %v", err)
	}

	registry, err = consul.NewClient(consulAddr)
	if err != nil {
		log.Errorf("got error while initializing consul agent: %v", err)
	}

	initializeDatabase()
}

// RecommendationService 定义了推荐服务的 gRPC 实现
type RecommendationService struct {
	pb.UnimplementedRecommendationServiceServer
}

// ListRecommendations 是 ListRecommendations gRPC 方法的实现
func (s *RecommendationService) ListRecommendations(ctx context.Context, req *pb.ListRecommendationsRequest) (*pb.ListRecommendationsResponse, error) {
	// 最大返回数量
	maxResponses := 3

	// TODO：从数据库中获取产品列表
	// TODO: 每个用户推荐的是不一样的数据
	products := make([]*pb.Product, 0)

	// 创建一个映射用来存储产品ID的布尔值
	productIDs := make(map[string]bool)
	// 将请求中的产品ID添加到映射中，并设置为true
	for _, product := range req.ProductIds {
		productIDs[product] = true
	}

	// 创建一个空的字符串切片用来存储过滤后的产品
	var filteredProducts []string
	// 遍历所有产品
	for _, product := range products {
		// 如果产品ID不在请求的产品ID列表中，则将该产品添加到过滤后的产品列表中
		if !productIDs[product.Id] {
			filteredProducts = append(filteredProducts, product.Id)
		}
	}

	// 计算过滤后产品的数量
	numProducts := len(filteredProducts)
	// 确定要返回的产品数量，取最小值，避免返回超出最大响应数的产品
	numReturn := min(maxResponses, numProducts)

	// 从过滤后的产品列表中随机选择要返回的产品的索引
	randIndices := generateRandomIndices(numReturn, numProducts)

	// 创建一个空的字符串切片，用来存储最终返回的产品列表
	var prodList []string
	// 根据随机选择的索引，从过滤后的产品列表中获取相应的产品，并添加到最终返回的产品列表中
	for _, idx := range randIndices {
		prodList = append(prodList, filteredProducts[idx])
	}

	fmt.Printf("[Recv ListRecommendations] product_ids=%v\n", prodList)
	// 构建并返回响应
	return &pb.ListRecommendationsResponse{
		ProductIds: prodList,
	}, nil
}

// Check 是健康检查服务的实现
func (s *RecommendationService) Check(ctx context.Context, req *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{
		Status: healthpb.HealthCheckResponse_SERVING,
	}, nil
}

// Watch 是健康检查服务的实现
func (s *RecommendationService) Watch(req *healthpb.HealthCheckRequest, srv healthpb.Health_WatchServer) error {
	return nil
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	// recommend service
	svc := &RecommendationService{}

	lis, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		log.Fatal(err)
	}

	opts := []grpc.ServerOption{
		grpc.KeepaliveParams(keepalive.ServerParameters{
			Timeout: 120 * time.Second,
		}),
		grpc.KeepaliveEnforcementPolicy(keepalive.EnforcementPolicy{
			PermitWithoutStream: true,
		}),
		grpc.UnaryInterceptor(
			otgrpc.OpenTracingServerInterceptor(Tracer),
		),
	}

	var srv = grpc.NewServer(opts...)

	// recommend service
	pb.RegisterRecommendationServiceServer(srv, svc)
	healthpb.RegisterHealthServer(srv, svc)
	log.Infof("starting to listen on tcp: %q", lis.Addr().String())

	portInt, _ := strconv.Atoi(port)
	svcUuid := uuid.New().String()
	err = registry.Register(name, svcUuid, "", portInt)
	if err != nil {
		log.Errorf("failed register: %v", err)
	}

	err = srv.Serve(lis)
	log.Fatal(err)
}

// generateRandomIndices 生成 [0, n) 范围内 numReturn 个不重复的随机数
func generateRandomIndices(numReturn, n int) []int {
	randIndices := make([]int, numReturn)
	indices := make(map[int]bool)
	for i := 0; i < numReturn; {
		rand.Seed(time.Now().UnixNano())
		idx := rand.Intn(n)
		if !indices[idx] {
			indices[idx] = true
			randIndices[i] = idx
			i++
		}
	}
	return randIndices
}
