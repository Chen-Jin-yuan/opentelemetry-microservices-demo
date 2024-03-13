package main

import (
	"fmt"
	"github.com/Chen-Jin-yuan/grpc/consul"
	"github.com/google/uuid"
	"github.com/grpc-ecosystem/grpc-opentracing/go/otgrpc"
	"github.com/opentracing/opentracing-go"
	"github.com/sirupsen/logrus"
	"google.golang.org/grpc"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/keepalive"
	pb "hipstershop"
	"net"
	"os"
	"strconv"
	"time"
	"tracing"
)

const (
	listenPort = "7070"
	name       = "cartservice"
	consulAddr = "consul:8500"
	jaegeraddr = "jaeger:6831"
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
	Tracer, err = tracing.Init("checkoutservice", jaegeraddr)
	if err != nil {
		log.Errorf("Got error while initializing jaeger agent: %v", err)
	}

	registry, err = consul.NewClient(consulAddr)
	if err != nil {
		log.Errorf("got error while initializing consul agent: %v", err)
	}
}

func main() {
	port := listenPort

	// Configure Redis client
	redisAddress := os.Getenv("REDIS_ADDR")
	if redisAddress == "" {
		fmt.Println("Redis cache host(hostname+port) was not specified.")
		fmt.Println("This sample was modified to showcase OpenTelemetry RedisInstrumentation.")
		fmt.Println("REDIS_ADDR environment variable is required.")
		os.Exit(1)
	}

	redisStore := NewRedisCartStore(redisAddress)
	err := redisStore.InitializeAsync()
	if err != nil {
		log.Fatal(err)
	}

	svc := NewCartService(redisStore)

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

	pb.RegisterCartServiceServer(srv, svc)
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
