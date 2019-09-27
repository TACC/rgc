<img align="center" alt="rgc_logo", width="300", src="docs/images/rgc_logo.svg">

Rolling Gantry Crane
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
		- gzynda/build-essential:bionic
	- Programs that exist in `-p` percent of images
- Generates Lmod files with
	- Metadata
	- Exposed executables

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
