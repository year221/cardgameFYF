.PHONY: build build-shell no-cache help

BASE_IMAGE := python:3.7

REPO = cardgamefyf
NAME = fyf
TAG := 1.0

IMAGE := ${REPO}/${NAME}

DOCKER_USER := --user=`id -u`
CONTAINER_NAME := ${USER}_$(shell date +%m-%d_%H%m%S)

BUILD_FLAGS = 

build:
	@echo "Building ${IMAGE} from ${BASE_IMAGE}..."
	@docker build ${BUILD_FLAGS} \
			--build-arg BASE_IMAGE=${BASE_IMAGE} \
			-f Dockerfile \
			-t ${IMAGE}:latest .

push: build
	@docker tag ${IMAGE}:latest ${IMAGE}:${TAG}
	@docker push ${IMAGE}:latest
	@docker push ${IMAGE}:${TAG}

no-cache:
	@echo "Using --no-cache"
	$(eval BUILD_FLAGS += "--no-cache")

build-shell:
	@docker run --rm -it \
	        --name=$(CONTAINER_NAME)
			${REPO}/${IMAGE}:${TAG} \
			/bin/sh