// Copyright 2018 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package main

import (
	"context"
	"flag"
	"fmt"
	"github.com/Chen-Jin-yuan/grpc/consul"
	"github.com/google/uuid"
	"gopkg.in/mgo.v2"
	"gopkg.in/mgo.v2/bson"
	"net"
	"os"
	"strconv"
	"strings"
	"time"

	pb "github.com/GoogleCloudPlatform/microservices-demo/src/productcatalogservice/genproto/hipstershop"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"

	"github.com/sirupsen/logrus"

	"go.opentelemetry.io/contrib/instrumentation/google.golang.org/grpc/otelgrpc"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
	"go.opentelemetry.io/otel/propagation"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
)

const name = "productcatalogservice"
const consulAddr = "consul:8500"

var (
	//cat          pb.ListProductsResponse
	//catalogMutex *sync.Mutex
	log          *logrus.Logger
	extraLatency time.Duration
	collection   *mgo.Collection

	port = "3550"

	//reloadCatalog bool
)

func init() {
	log = logrus.New()
	log.Formatter = &logrus.JSONFormatter{
		FieldMap: logrus.FieldMap{
			logrus.FieldKeyTime:  "timestamp",
			logrus.FieldKeyLevel: "severity",
			logrus.FieldKeyMsg:   "message",
		},
		TimestampFormat: time.RFC3339Nano,
	}
	log.Out = os.Stdout
	//catalogMutex = &sync.Mutex{}
	//err := readCatalogFile(&cat)
	//if err != nil {
	//	log.Warnf("could not parse product catalog")
	//}
	initializeDatabase()
	GetProducts()
}

func InitTracerProvider() *sdktrace.TracerProvider {
	ctx := context.Background()

	exporter, err := otlptracegrpc.New(ctx)
	if err != nil {
		log.Fatal(err)
	}
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithSampler(sdktrace.AlwaysSample()),
		sdktrace.WithBatcher(exporter),
	)
	otel.SetTracerProvider(tp)
	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
	return tp
}

func main() {
	tp := InitTracerProvider()
	defer func() {
		if err := tp.Shutdown(context.Background()); err != nil {
			log.Printf("Error shutting down tracer provider: %v", err)
		}
	}()

	flag.Parse()

	// set injected latency
	if s := os.Getenv("EXTRA_LATENCY"); s != "" {
		v, err := time.ParseDuration(s)
		if err != nil {
			log.Fatalf("failed to parse EXTRA_LATENCY (%s) as time.Duration: %+v", v, err)
		}
		extraLatency = v
		log.Infof("extra latency enabled (duration: %v)", extraLatency)
	} else {
		extraLatency = time.Duration(0)
	}

	//sigs := make(chan os.Signal, 1)
	//signal.Notify(sigs, syscall.SIGUSR1, syscall.SIGUSR2)
	//go func() {
	//	for {
	//		sig := <-sigs
	//		log.Printf("Received signal: %s", sig)
	//		if sig == syscall.SIGUSR1 {
	//			reloadCatalog = true
	//			log.Infof("Enable catalog reloading")
	//		} else {
	//			reloadCatalog = false
	//			log.Infof("Disable catalog reloading")
	//		}
	//	}
	//}()

	if os.Getenv("PORT") != "" {
		port = os.Getenv("PORT")
	}
	log.Infof("starting grpc server at :%s", port)
	run(port)
	select {}
}

func run(port string) string {
	l, err := net.Listen("tcp", fmt.Sprintf(":%s", port))
	if err != nil {
		log.Fatal(err)
	}
	var srv *grpc.Server = grpc.NewServer(
		grpc.UnaryInterceptor(otelgrpc.UnaryServerInterceptor()),
		grpc.StreamInterceptor(otelgrpc.StreamServerInterceptor()),
	)

	svc := &productCatalog{}

	pb.RegisterProductCatalogServiceServer(srv, svc)
	healthpb.RegisterHealthServer(srv, svc)

	registry, err := consul.NewClient(consulAddr)
	if err != nil {
		log.Errorf("got error while initializing consul agent: %v", err)
	}
	portInt, _ := strconv.Atoi(port)
	svcUuid := uuid.New().String()
	err = registry.Register(name, svcUuid, "", portInt)
	if err != nil {
		log.Errorf("failed register: %v", err)
	}

	go srv.Serve(l)
	return l.Addr().String()
}

type productCatalog struct {
	pb.UnimplementedProductCatalogServiceServer
}

func GetProducts() []*pb.Product {
	// 查询MongoDB集合中的所有文档
	var mongoProducts []Product
	err := collection.Find(bson.M{}).All(&mongoProducts)
	if err != nil {
		log.Fatalf("Error querying MongoDB collection: %v", err)
	}

	// 将MongoDB产品转换为pb.Product类型并添加到切片中
	var products []*pb.Product
	for _, mp := range mongoProducts {
		priceUsd := &pb.Money{
			CurrencyCode: mp.PriceUsd.CurrencyCode,
			Units:        mp.PriceUsd.Units,
			Nanos:        mp.PriceUsd.Nanos,
		}
		product := &pb.Product{
			Id:          mp.Id,
			Name:        mp.Name,
			Description: mp.Description,
			Picture:     mp.Picture,
			PriceUsd:    priceUsd,
			Categories:  mp.Categories,
		}
		products = append(products, product)
	}

	// 输出读取到的产品数量
	log.Printf("Read %d products from MongoDB\n", len(products))

	return products
}

// replace: 从数据库里读 product
//func readCatalogFile(catalog *pb.ListProductsResponse) error {
//	catalogMutex.Lock()
//	defer catalogMutex.Unlock()
//	catalogJSON, err := ioutil.ReadFile("products.json")
//	if err != nil {
//		log.Fatalf("failed to open product catalog json file: %v", err)
//		return err
//	}
//	if err := protojson.Unmarshal(catalogJSON, catalog); err != nil {
//		log.Warnf("failed to parse the catalog JSON: %v", err)
//		return err
//	}
//	log.Info("successfully parsed product catalog json")
//	return nil
//}
//
//func parseCatalog() []*pb.Product {
//	if reloadCatalog || len(cat.Products) == 0 {
//		err := readCatalogFile(&cat)
//		if err != nil {
//			return []*pb.Product{}
//		}
//	}
//	return cat.Products
//}

func (p *productCatalog) Check(ctx context.Context, req *healthpb.HealthCheckRequest) (*healthpb.HealthCheckResponse, error) {
	return &healthpb.HealthCheckResponse{Status: healthpb.HealthCheckResponse_SERVING}, nil
}

func (p *productCatalog) Watch(req *healthpb.HealthCheckRequest, ws healthpb.Health_WatchServer) error {
	return status.Errorf(codes.Unimplemented, "health check via Watch not implemented")
}

func (p *productCatalog) ListProducts(context.Context, *pb.Empty) (*pb.ListProductsResponse, error) {
	time.Sleep(extraLatency)
	return &pb.ListProductsResponse{Products: GetProducts()}, nil
}

func (p *productCatalog) GetProduct(ctx context.Context, req *pb.GetProductRequest) (*pb.Product, error) {
	time.Sleep(extraLatency)
	var found *pb.Product
	// 可以直接从数据库查询 id
	products := GetProducts()
	for i := 0; i < len(products); i++ {
		if req.Id == products[i].Id {
			found = products[i]
		}
	}
	if found == nil {
		return nil, status.Errorf(codes.NotFound, "no product with ID %s", req.Id)
	}
	return found, nil
}

func (p *productCatalog) SearchProducts(ctx context.Context, req *pb.SearchProductsRequest) (*pb.SearchProductsResponse, error) {
	time.Sleep(extraLatency)
	// Intepret query as a substring match in name or description.
	var ps []*pb.Product
	for _, p := range GetProducts() {
		if strings.Contains(strings.ToLower(p.Name), strings.ToLower(req.Query)) ||
			strings.Contains(strings.ToLower(p.Description), strings.ToLower(req.Query)) {
			ps = append(ps, p)
		}
	}
	return &pb.SearchProductsResponse{Results: ps}, nil
}
