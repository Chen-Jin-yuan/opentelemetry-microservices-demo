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
	"fmt"
	"net/http"
	"os"
	"time"

	"github.com/Chen-Jin-yuan/grpc/consul"
	"github.com/Chen-Jin-yuan/grpc/dialer"
	"github.com/harlow/go-micro-services/tracing"
	"github.com/pkg/errors"

	"github.com/opentracing/opentracing-go"
	"google.golang.org/grpc"
	// "go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc"
)

const (
	port            = "8080"
	defaultCurrency = "USD"
	cookieMaxAge    = 60 * 60 * 48

	cookiePrefix    = "shop_"
	cookieSessionID = cookiePrefix + "session-id"
	cookieCurrency  = cookiePrefix + "currency"

	consulAddr = "consul:8500"
	jaegeraddr = "jaeger:6831"
)

var (
	whitelistedCurrencies = map[string]bool{
		"USD": true,
		"EUR": true,
		"CAD": true,
		"JPY": true,
		"GBP": true,
		"TRY": true}
	registry *consul.Client
	Tracer   opentracing.Tracer
)

type ctxKeySessionID struct{}

type frontendServer struct {
	productCatalogSvcAddr string
	productCatalogSvcConn *grpc.ClientConn

	currencySvcAddr string
	currencySvcConn *grpc.ClientConn

	cartSvcAddr string
	cartSvcConn *grpc.ClientConn

	recommendationSvcAddr string
	recommendationSvcConn *grpc.ClientConn

	checkoutSvcAddr string
	checkoutSvcConn *grpc.ClientConn

	shippingSvcAddr string
	shippingSvcConn *grpc.ClientConn

	adSvcAddr string
	adSvcConn *grpc.ClientConn
}

//func InitTracerProvider() *sdktrace.TracerProvider {
//	ctx := context.Background()
//
//	exporter, err := otlptracegrpc.New(ctx)
//	if err != nil {
//		log.Fatal(err)
//	}
//	tp := sdktrace.NewTracerProvider(
//		sdktrace.WithSampler(sdktrace.AlwaysSample()),
//		sdktrace.WithBatcher(exporter),
//	)
//	otel.SetTracerProvider(tp)
//	otel.SetTextMapPropagator(propagation.NewCompositeTextMapPropagator(propagation.TraceContext{}, propagation.Baggage{}))
//	return tp
//}

func main() {
	//tp := InitTracerProvider()
	//defer func() {
	//	if err := tp.Shutdown(context.Background()); err != nil {
	//		log.Printf("Error shutting down tracer provider: %v", err)
	//	}
	//}()
	var err error
	Tracer, err = tracing.Init("frontend", jaegeraddr)
	if err != nil {
		log.Errorf("Got error while initializing jaeger agent: %v", err)
	}

	ctx := context.Background()

	srvPort := port
	if os.Getenv("PORT") != "" {
		srvPort = os.Getenv("PORT")
	}
	addr := os.Getenv("LISTEN_ADDR")
	svc := new(frontendServer)
	mustMapEnv(&svc.productCatalogSvcAddr, "PRODUCT_CATALOG_SERVICE_ADDR")
	mustMapEnv(&svc.currencySvcAddr, "CURRENCY_SERVICE_ADDR")
	mustMapEnv(&svc.cartSvcAddr, "CART_SERVICE_ADDR")
	mustMapEnv(&svc.recommendationSvcAddr, "RECOMMENDATION_SERVICE_ADDR")
	mustMapEnv(&svc.checkoutSvcAddr, "CHECKOUT_SERVICE_ADDR")
	mustMapEnv(&svc.shippingSvcAddr, "SHIPPING_SERVICE_ADDR")
	mustMapEnv(&svc.adSvcAddr, "AD_SERVICE_ADDR")

	registry, err = consul.NewClient(consulAddr)
	if err != nil {
		log.Errorf("got error while initializing consul agent: %v", err)
	}

	//mustConnGRPC(ctx, &svc.currencySvcConn, svc.currencySvcAddr)
	// mustConnGRPC(ctx, &svc.productCatalogSvcConn, svc.productCatalogSvcAddr)
	//mustConnGRPC(ctx, &svc.cartSvcConn, svc.cartSvcAddr)
	// mustConnGRPC(ctx, &svc.recommendationSvcConn, svc.recommendationSvcAddr)
	// mustConnGRPC(ctx, &svc.shippingSvcConn, svc.shippingSvcAddr)
	// mustConnGRPC(ctx, &svc.checkoutSvcConn, svc.checkoutSvcAddr)
	// mustConnGRPC(ctx, &svc.adSvcConn, svc.adSvcAddr)

	mustConnGRPCNew(ctx, &svc.shippingSvcConn, "shippingservice")
	mustConnGRPCNew(ctx, &svc.checkoutSvcConn, "checkoutservice")
	mustConnGRPCNew(ctx, &svc.productCatalogSvcConn, "productcatalogservice")
	mustConnGRPCNew(ctx, &svc.recommendationSvcConn, "recommendationservice")
	mustConnGRPCNew(ctx, &svc.adSvcConn, "adservice")
	mustConnGRPCNew(ctx, &svc.cartSvcConn, "cartservice")
	mustConnGRPCNew(ctx, &svc.currencySvcConn, "currencyservice")

	r := tracing.NewServeMux(Tracer)
	r.Handle("/", http.HandlerFunc(svc.homeHandler))
	r.Handle("/product", http.HandlerFunc(svc.productHandler))
	r.Handle("/cart/view", http.HandlerFunc(svc.viewCartHandler))
	r.Handle("/cart/add", http.HandlerFunc(svc.addToCartHandler))
	r.Handle("/cart/empty", http.HandlerFunc(svc.emptyCartHandler))
	r.Handle("/setCurrency", http.HandlerFunc(svc.setCurrencyHandler))
	r.Handle("/logout", http.HandlerFunc(svc.logoutHandler))
	r.Handle("/cart/checkout", http.HandlerFunc(svc.placeOrderHandler))

	// r := tracing.NewServeMux(Tracer)
	// r.Use(otelmux.Middleware("server"))
	// r.HandleFunc("/", svc.homeHandler).Methods(http.MethodGet, http.MethodHead)
	// r.HandleFunc("/product/{id}", svc.productHandler).Methods(http.MethodGet, http.MethodHead)
	// r.HandleFunc("/cart", svc.viewCartHandler).Methods(http.MethodGet, http.MethodHead)
	// r.HandleFunc("/cart", svc.addToCartHandler).Methods(http.MethodPost)
	// r.HandleFunc("/cart/empty", svc.emptyCartHandler).Methods(http.MethodPost)
	// r.HandleFunc("/setCurrency", svc.setCurrencyHandler).Methods(http.MethodPost)
	// r.HandleFunc("/logout", svc.logoutHandler).Methods(http.MethodGet)
	// r.HandleFunc("/cart/checkout", svc.placeOrderHandler).Methods(http.MethodPost)
	// r.PathPrefix("/static/").Handler(http.StripPrefix("/static/", http.FileServer(http.Dir("./static/"))))
	// r.HandleFunc("/robots.txt", func(w http.ResponseWriter, _ *http.Request) { fmt.Fprint(w, "User-agent: *\nDisallow: /") })
	// r.HandleFunc("/_healthz", func(w http.ResponseWriter, _ *http.Request) { fmt.Fprint(w, "ok") })

	var handler http.Handler = r
	handler = &logHandler{log: log, next: handler} // add logging
	handler = ensureSessionID(handler)             // add session ID

	log.Infof("starting server on " + addr + ":" + srvPort)
	log.Fatal(http.ListenAndServe(addr+":"+srvPort, handler))
}

func mustMapEnv(target *string, envKey string) {
	v := os.Getenv(envKey)
	if v == "" {
		panic(fmt.Sprintf("environment variable %q not set", envKey))
	}
	*target = v
}

func mustConnGRPC(ctx context.Context, conn **grpc.ClientConn, addr string) {
	var err error
	ctx, cancel := context.WithTimeout(ctx, time.Second*3)
	defer cancel()
	*conn, err = grpc.DialContext(ctx, addr,
		grpc.WithInsecure())
	//grpc.WithTransportCredentials(insecure.NewCredentials()),
	//grpc.WithUnaryInterceptor(otelgrpc.UnaryClientInterceptor()),
	//grpc.WithStreamInterceptor(otelgrpc.StreamClientInterceptor()),

	if err != nil {
		panic(errors.Wrapf(err, "grpc: failed to connect %s", addr))
	}
}

func mustConnGRPCNew(ctx context.Context, conn **grpc.ClientConn, addr string) {
	var err error
	ctx, cancel := context.WithTimeout(ctx, time.Second*3)
	defer cancel()
	*conn, err = dialer.Dial(
		addr,
		dialer.WithTracer(Tracer),
		dialer.WithBalancerRR(registry),
	)
	if err != nil {
		panic(errors.Wrapf(err, "grpc: failed to connect %s", addr))
	}
}
