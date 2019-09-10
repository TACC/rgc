RGCV := $(shell grep "VERSION =" setup.py | cut -d \" -f 2)
PYV := $(shell python --version | cut -d ' ' -f 2 | cut -d . -f 1)

README.md:
	bash extras/make_readme.sh

gzynda/rgc:
	python setup.py bdist_wheel
	docker build --build-arg RGCV=$(RGCV) --build-arg PYV=$(PYV) -t gzynda/rgc:latest -f extras/Dockerfile .
gzynda/build-essential:
	docker build --build-arg UBV=bionic -t $@:bionic -f extras/Dockerfile.build-essential .
	docker push $@:bionic

all: README.md gzynda/rgc gzynda/build-essential
