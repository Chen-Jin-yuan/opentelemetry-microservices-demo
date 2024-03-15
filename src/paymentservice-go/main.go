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
	listenPort = "50051"
	name       = "paymentservice"
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
	// payment service
	Tracer, err = tracing.Init(name, jaegerAddr)
	if err != nil {
		log.Errorf("Got error while initializing jaeger agent: %v", err)
	}

	registry, err = consul.NewClient(consulAddr)
	if err != nil {
		log.Errorf("got error while initializing consul agent: %v", err)
	}
}

// PaymentService 实现了 PaymentService 服务
type PaymentService struct {
	pb.UnimplementedPaymentServiceServer
}

// Charge 实现了 PaymentService.Charge 方法
func (s *PaymentService) Charge(ctx context.Context, req *pb.ChargeRequest) (*pb.ChargeResponse, error) {
	// 在此处调用 ChargeHandler 函数进行支付处理
	return ChargeHandler(req)
}

// Check 是健康检查服务的实现
func (s *PaymentService) Check(ctx context.Context, req *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{
		Status: healthpb.HealthCheckResponse_SERVING,
	}, nil
}

// Watch 是健康检查服务的实现
func (s *PaymentService) Watch(req *healthpb.HealthCheckRequest, srv healthpb.Health_WatchServer) error {
	return nil
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = listenPort
	}

	// payment service
	svc := &PaymentService{}

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

	// payment service
	pb.RegisterPaymentServiceServer(srv, svc)
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
