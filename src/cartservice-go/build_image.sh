#!/bin/bash

tag="-delphinus"
service="cartservice"
name="$service$tag"

# 打印docker build命令
build_command="docker build -t opentelemetry:$name ."
echo "Running command: $build_command"

# 检查docker build是否成功
if ! $build_command; then
    echo "Docker build failed."
    exit 1
fi

# 打印docker tag命令
tag_command="docker tag opentelemetry:$name chenjinyuan/opentelemetry:$name"
echo "Running command: $tag_command"

# 检查docker tag是否成功
if ! $tag_command; then
    echo "Docker tagging failed."
    exit 1
fi

# 打印docker push命令
push_command="docker push chenjinyuan/opentelemetry:$name"
echo "Running command: $push_command"

# 检查docker push是否成功
if ! $push_command; then
    echo "Docker push failed."
    exit 1
fi

echo "Docker image pushed successfully."
