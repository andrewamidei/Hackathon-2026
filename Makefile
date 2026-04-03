IMAGENAME=musicongo
CONTAINERNAME=dug
src = .

PWD = $(shell pwd)

.PHONY: run

.PHONY: clean

.PHONY: build

TARGET_DIR ?= $(PWD)

run:
	docker b	

clean:
	docker prune

build:
	./build.sh
	
