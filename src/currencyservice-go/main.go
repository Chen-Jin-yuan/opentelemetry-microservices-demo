package main

import (
	"context"
	"encoding/json"
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
	"io/ioutil"
	"math"
	"net"
	"os"
	"strconv"
	"time"
	"tracing"
)

const (
	listenPort = "7000"
	name       = "currencyservice"
	consulAddr = "consul:8500"
	jaegerAddr = "jaeger:6831"
)

var (
	log          *logrus.Logger
	registry     *consul.Client
	Tracer       opentracing.Tracer
	currencyData map[string]float64
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
	// currency service
	Tracer, err = tracing.Init(name, jaegerAddr)
	if err != nil {
		log.Errorf("Got error while initializing jaeger agent: %v", err)
	}

	registry, err = consul.NewClient(consulAddr)
	if err != nil {
		log.Errorf("got error while initializing consul agent: %v", err)
	}

	loadCurrencyData()
}

// loadCurrencyData loads currency data from the JSON file.
func loadCurrencyData() {
	if currencyData != nil {
		return
	}

	currencyData = make(map[string]float64)

	data, err := ioutil.ReadFile("data/currency_conversion.json")
	if err != nil {
		log.Fatalf("Error reading currency data: %v", err)
	}

	var rawCurrencyData map[string]string
	if err := json.Unmarshal(data, &rawCurrencyData); err != nil {
		log.Fatalf("Error parsing currency data: %v", err)
	}

	for key, value := range rawCurrencyData {
		rate, err := strconv.ParseFloat(value, 64)
		if err != nil {
			log.Fatalf("Error parsing currency rate for %s: %v", key, err)
		}
		currencyData[key] = rate
	}
}

// carry handles decimal/fractional carrying.
func carry(units, nanos float64) (float64, float64) {
	fractionSize := math.Pow(10, 9)
	nanos += math.Mod(units, 1) * fractionSize
	units = math.Floor(units) + math.Floor(nanos/fractionSize)
	nanos = math.Mod(nanos, fractionSize)
	return units, nanos
}

// CurrencyService implements the CurrencyService gRPC service.
type CurrencyService struct {
	pb.UnimplementedCurrencyServiceServer
}

// GetSupportedCurrencies returns the supported currencies.
func (s *CurrencyService) GetSupportedCurrencies(ctx context.Context, in *pb.Empty) (*pb.GetSupportedCurrenciesResponse, error) {
	var currencyCodeKeys []string
	for currencyCode := range currencyData {
		currencyCodeKeys = append(currencyCodeKeys, currencyCode)
	}
	return &pb.GetSupportedCurrenciesResponse{CurrencyCodes: currencyCodeKeys}, nil
}

// Convert converts between currencies.
func (s *CurrencyService) Convert(ctx context.Context, in *pb.CurrencyConversionRequest) (*pb.Money, error) {
	from := in.GetFrom()
	fromUnits := float64(from.Units)
	fromNanos := float64(from.Nanos)

	// Convert: from_currency --> EUR
	eurosUnits, euroNanos := carry(fromUnits/currencyData[from.CurrencyCode],
		fromNanos/currencyData[from.CurrencyCode])

	euroNanos = math.Round(euroNanos)

	// Convert: EUR --> to_currency
	toCode := in.GetToCode()
	resultUnits, resultNanos := carry(eurosUnits*currencyData[toCode],
		euroNanos*currencyData[toCode])

	return &pb.Money{
		CurrencyCode: toCode,
		Units:        int64(math.Floor(resultUnits)),
		Nanos:        int32(math.Floor(resultNanos)),
	}, nil
}

// Check 是健康检查服务的实现
func (s *CurrencyService) Check(ctx context.Context, req *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{
		Status: healthpb.HealthCheckResponse_SERVING,
	}, nil
}

// Watch 是健康检查服务的实现
func (s *CurrencyService) Watch(req *healthpb.HealthCheckRequest, srv healthpb.Health_WatchServer) error {
	return nil
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = listenPort
	}

	// currency service
	svc := &CurrencyService{}

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

	// currency service
	pb.RegisterCurrencyServiceServer(srv, svc)
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
