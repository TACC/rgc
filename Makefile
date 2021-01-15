RGCV := $(shell grep "VERSION =" setup.py | cut -d \" -f 2)
PYV := $(shell python --version 2>&1 | cut -d ' ' -f 2 | cut -d . -f 1)

IMG=gzynda/rgc
TESTC=rgc_test_container
TEST=rgc_test_env

test_env: extras/Dockerfile.test_env
	docker rm -f $(TEST); docker build -t $(TESTC) -f $< ./extras && docker system prune -f
	docker run --privileged --rm -d --name $(TEST) -v $(PWD):/root/rgc $(TESTC)
	#docker run --rm -it -d --name $(TEST) -v /var/run/docker.sock:/var/run/docker.sock -v $(PWD):/root/rgc -v /tmp:/tmp $(TESTC) /bin/sh
	docker exec -it $(TEST) pip3 install -e /root/rgc
	docker exec -it $(TEST) bash --login; docker rm -f $(TEST)

README.md: extras/intro.md extras/examples.md s3 s2
	cat extras/intro.md > $@
	docker run gzynda/rgc:latest rgc -h >> $@
	cat extras/examples.md >> $@

dist/rgc-$(RGCV)-py$(PYV)-none-any.whl: rgc/__init__.py
	python setup.py bdist_wheel
dist/current_source.tar.gz: setup.py tests/__init__.py rgc/__init__.py
	tar -czf $@ rgc setup.py tests
s3: dist/rgc-$(RGCV)-py$(PYV)-none-any.whl
	docker build --build-arg RGCV=$(RGCV) --build-arg PYV=$(PYV) -t gzynda/rgc:$(RGCV)_$@ -f extras/Dockerfile.$@ .
	docker tag $(IMG):$(RGCV)_$@ $(IMG):latest
	for img in $(IMG):{$(RGCV)_$@,latest}; do echo "Pushing $$img"; docker push $$img; done
gzynda/build-essential:
	docker pull $@:bionic
	docker build --build-arg UBV=bionic -t $@:bionic -f extras/Dockerfile.build-essential .
	docker push $@:bionic
sing: s3
test: s3 gzynda/build-essential dist/current_source.tar.gz
	docker run --privileged -v $$PWD/dist:/dist --rm -it gzynda/rgc:$(RGCV)_s3 bash -lc 'ls -lh /dist && tar -xzf /dist/current_source.tar.gz && python3 setup.py test' \
	&& docker run --privileged --rm -it gzynda/rgc:$(RGCV)_s3 bash -lc 'rgc biocontainers/bwa:0.7.15 && rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 && module use ~/modulefiles && module load samtools bwa && samtools 2>&1 | grep -q Usage && bwa 2>&1 | grep -q Usage'

all: README.md sing gzynda/build-essential
