gantry-crane
======================================================

Pulls containers from either:

- docker hub
- quay.io

and generates Lmod modulefiles for us on HPC systems.

Requirements
------------------------------------------------------

- docker or singularity
- python

Usage
------------------------------------------------------

```
usage: gantry-crane [-h] [-I PATH] [-M PATH] [-P STR] [-p INT] [-S] [-v]
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
  -P STR, --prefix STR  Prefix string to image directory for when an
                        environment variable is used - not used by default
  -p INT, --percentile INT
                        Remove packages that [25]
  -S, --singularity     Images are cached as singularity containers - even
                        when docker is present
  -v, --verbose         Enable verbose logging
```
