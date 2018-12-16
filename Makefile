.DEFAULT_GOAL:=build
HEROKU_APP?=staticmaps

.PHONY: install
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

.PHONY: build
build: C=$(shell git rev-parse HEAD)
build: BT="$(shell date)"
build: BUILD_ARGS=--build-arg COMMIT=$(C) --build-arg BUILD_TIME=$(BT)
build:
	docker build . -t static-maps $(BUILD_ARGS)

.PHONY: push
push: build
	docker tag static-maps registry.heroku.com/$(HEROKU_APP)/web
	docker push registry.heroku.com/$(HEROKU_APP)/web

.PHONY: release
release: push
	heroku container:release web worker -a $(HEROKU_APP)
