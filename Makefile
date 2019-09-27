RGCV := $(shell grep "VERSION =" setup.py | cut -d \" -f 2)
PYV := $(shell python --version 2>&1 | cut -d ' ' -f 2 | cut -d . -f 1)
IMG=gzynda/rgc

README.md: extras/intro.md extras/examples.md s3 s2
	cat extras/intro.md > $@
	docker run gzynda/rgc:latest rgc -h >> $@
	cat extras/examples.md >> $@

dist/rgc-$(RGCV)-py$(PYV)-none-any.whl: rgc/__init__.py
	python setup.py bdist_wheel
s3 s2: dist/rgc-$(RGCV)-py$(PYV)-none-any.whl
	docker build --build-arg RGCV=$(RGCV) --build-arg PYV=$(PYV) -t gzynda/rgc:$(RGCV)_$@ -f extras/Dockerfile.$@ .
	docker tag $(IMG):$(RGCV)_$@ $(IMG):latest
	for img in $(IMG):{$(RGCV)_$@,latest}; do echo "Pushing $$img"; docker push $$img; done
gzynda/build-essential:
	docker build --build-arg UBV=bionic -t $@:bionic -f extras/Dockerfile.build-essential .
	docker push $@:bionic
sing: s3 s2
test: s3 s2
	docker run --privileged --rm -it gzynda/rgc:$(RGCV)_s2 bash -lc 'rgc biocontainers/bwa:0.7.15 && rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 && module use ~/modulefiles && module load samtools bwa && samtools 2>&1 | grep -q Usage && bwa 2>&1 | grep -q Usage'
	docker run --privileged --rm -it gzynda/rgc:$(RGCV)_s3 bash -lc 'rgc biocontainers/bwa:0.7.15 && rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 && module use ~/modulefiles && module load samtools bwa && samtools 2>&1 | grep -q Usage && bwa 2>&1 | grep -q Usage'

all: README.md sing gzynda/build-essential
