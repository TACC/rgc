rgc - Rolling Gantry Crane
======================================================

Pulls containers from either:

- [docker hub](https://hub.docker.com/)
- [quay.io](https://quay.io/)

and generates [Lmod](https://github.com/TACC/Lmod) modulefiles for use on HPC systems.

Workflow
------------------------------------------------------

- Validates each URL
  - Looks for name and tag on specified repsoitory
  - Excludes packages that are classified as Libraries on bio.tools
- Pulls data for each URL
  - Container
  - Metadata from
    - bio.tools
    - launchpad
- Scans programs on each container's `$PATH`
- Filters out programs based on the following criteria
  - Programs exist in baseline images
    - ubuntu:xenial
    - centos:7
    - ubuntu:bionic
    - continuumio/miniconda:latest
    - biocontainers/biocontainers:latest
    - gzynda/singularity:2.6.0
  - Programs that exist in `-p` percent of images
- Generates Lmod files

Requirements
------------------------------------------------------

- docker or singularity
- python 2 or 3
  - tqdm

Platorms
------------------------------------------------------

- Linux
- MacOS

Usage
------------------------------------------------------

```
usage: rgc [-h] [-I PATH] [-M PATH] [-r STR] [-C STR] [-P STR]
                   [-p INT] [-S] [-t INT] [-v]
                   URL [URL ...]

positional arguments:
  URL                   Image urls to pull

optional arguments:
  -h, --help            show this help message and exit
  -I PATH, --imgdir PATH
                        Directory used to cache singularity images
                        [./containers]
  -M PATH, --moddir PATH
                        Path to modulefiles [./modulefiles]
  -r STR, --requires STR
                        Module prerequisites separated by "," []
  -C STR, --contact STR
                        Contact URL(s) in modules separated by ","
                        [https://github.com/zyndagj/rgc/issues]
  -P STR, --prefix STR  Prefix string to image directory for when an
                        environment variable is used - not used by default
  -p INT, --percentile INT
                        Exclude programs in >= p% of images [25]
  -S, --singularity     Images are cached as singularity containers - even
                        when docker is present
  -t INT, --threads INT
                        Number of concurrent threads to use for pulling [8]
  -v, --verbose         Enable verbose logging
```

Examples
------------------------------------------------------

Pulling and generating modules for bwa, samtools, and bowtie

```
rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 biocontainers/bowtie:v1.1.2_cv3
```

and if you don't have a system running Lmod, feel free to test in docker

```
$ docker run --privileged --rm -it gzynda/rgc:latest bash

$ rgc biocontainers/bwa:0.7.15 biocontainers/samtools:v1.7.0_cv3 biocontainers/bowtie:v1.1.2_cv3
$ module use ${PWD}/modulefiles
$ module avail
$ module load bwa
$ bwa
```
