.DEFAULT_GOAL:=all
HEROKU_APP?=static-maps

.PHONY: install
install:
	pip install -r requirements.txt
	pip install -r tests/requirements.txt
	pip install -r requirements-dev.txt

.PHONY: isort
isort:
	isort -w 120 app tests

.PHONY: lint
lint:
	flake8 app tests
	pytest -p no:sugar -q --cache-clear --isort app

.PHONY: test
test:
	pytest --cov=app --isort tests

.PHONY: testcov
testcov: test
	coverage html

.PHONY: all
all: testcov lint

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
release:
	heroku container:release web -a $(HEROKU_APP)

.PHONY: run
run: build
	docker run -it --rm -p 8000:8000 static-maps
