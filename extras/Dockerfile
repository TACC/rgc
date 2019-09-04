FROM fedora:29

RUN yum install -y git Lmod singularity-2.6.1 singularity-runtime-2.6.1 \
	&& yum clean all

ADD dist/rgc-0.1.0-py3-none-any.whl /root/rgc-0.1.0-py3-none-any.whl

RUN useradd -m testRGC \
	&& pip3 install /root/rgc-0.1.0-py3-none-any.whl \
	&& rm /root/rgc-0.1.0-py3-none-any.whl

USER testRGC
WORKDIR /home/testRGC
