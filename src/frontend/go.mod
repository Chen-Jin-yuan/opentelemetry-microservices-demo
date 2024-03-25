module github.com/GoogleCloudPlatform/microservices-demo/src/frontend

go 1.21.3

toolchain go1.21.5

replace github.com/harlow/go-micro-services/tracing => ./tracing

require (
	cloud.google.com/go/compute/metadata v0.2.0
	github.com/Chen-Jin-yuan/grpc/consul v1.0.3
	github.com/Chen-Jin-yuan/grpc/dialer v1.1.5
	github.com/google/uuid v1.3.1
	github.com/harlow/go-micro-services/tracing v0.0.0-00010101000000-000000000000
	github.com/opentracing/opentracing-go v1.2.0
	github.com/pkg/errors v0.9.1
	github.com/sirupsen/logrus v1.8.1
	google.golang.org/grpc v1.29.1
)

require (
	github.com/Chen-Jin-yuan/grpc/allocator v1.1.4 // indirect
	github.com/armon/go-metrics v0.4.1 // indirect
	github.com/fatih/color v1.14.1 // indirect
	github.com/golang/protobuf v1.5.3 // indirect
	github.com/google/go-cmp v0.6.0 // indirect
	github.com/grpc-ecosystem/grpc-opentracing v0.0.0-20180507213350-8e809c8a8645 // indirect
	github.com/hashicorp/consul/api v1.25.1 // indirect
	github.com/hashicorp/go-cleanhttp v0.5.2 // indirect
	github.com/hashicorp/go-hclog v1.5.0 // indirect
	github.com/hashicorp/go-immutable-radix v1.3.1 // indirect
	github.com/hashicorp/go-rootcerts v1.0.2 // indirect
	github.com/hashicorp/golang-lru v0.5.4 // indirect
	github.com/hashicorp/serf v0.10.1 // indirect
	github.com/mattn/go-colorable v0.1.13 // indirect
	github.com/mattn/go-isatty v0.0.19 // indirect
	github.com/mitchellh/go-homedir v1.1.0 // indirect
	github.com/mitchellh/mapstructure v1.5.0 // indirect
	github.com/opentracing-contrib/go-stdlib v1.0.0 // indirect
	github.com/rs/zerolog v1.31.0 // indirect
	github.com/stretchr/testify v1.8.4 // indirect
	github.com/uber/jaeger-client-go v2.30.0+incompatible // indirect
	github.com/uber/jaeger-lib v2.4.1+incompatible // indirect
	go.uber.org/atomic v1.11.0 // indirect
	golang.org/x/exp v0.0.0-20230321023759-10a507213a29 // indirect
	golang.org/x/net v0.18.0 // indirect
	google.golang.org/genproto/googleapis/rpc v0.0.0-20231002182017-d307bd883b97 // indirect
)

require (
	golang.org/x/sys v0.14.0 // indirect
	golang.org/x/text v0.14.0 // indirect
	google.golang.org/protobuf v1.31.0
)
