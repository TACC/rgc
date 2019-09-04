README.md:
	bash extras/make_readme.sh

gzynda/rgc:
	python setup.py bdist_wheel
	docker build -t gzynda/rgc:latest -f extras/Dockerfile .

all: README.md gzynda/rgc
