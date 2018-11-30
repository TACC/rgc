FROM fedora:29

RUN yum install Lmod singularity-2.6.0 singularity-runtime-2.6.0\
	&& useradd -m testRGC \
	&& pip install git+git@github.com:zyndagj/rgc.git

USER testRGC
