IMAGENAME=musicongo
CONTAINERNAME=dug
src = .

PWD = $(shell pwd)

.PHONY: run

.PHONY: clean

.PHONY: build

TARGET_DIR ?= $(PWD)

run:
	docker run -p 8501:8501 dug 

clean:
	docker prune

build:
	./build.sh
	
