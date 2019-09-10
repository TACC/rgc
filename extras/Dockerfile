FROM fedora:29
ARG RGCV
ARG PYV=3
ARG SINGV=2.6.0

RUN yum install -y git Lmod singularity-${SINGV} singularity-runtime-${SINGV} \
	&& yum clean all

ADD dist/rgc-${RGCV}-py${PYV}-none-any.whl /root/rgc-${RGCV}-py${PYV}-none-any.whl

RUN useradd -m testRGC \
	&& pip3 install /root/rgc-${RGCV}-py${PYV}-none-any.whl \
	&& rm /root/rgc-${RGCV}-py${PYV}-none-any.whl

USER testRGC
WORKDIR /home/testRGC
