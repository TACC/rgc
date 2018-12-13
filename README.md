rgc - Rolling Gantry Crane
======================================================

Pulls containers from either:

- docker hub
- quay.io

and generates Lmod modulefiles for use on HPC systems.

https://github.com/TACC/Lmod

Requirements
------------------------------------------------------

- docker or singularity
- python

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
                        Remove packages that [25]
  -S, --singularity     Images are cached as singularity containers - even
                        when docker is present
  -t INT, --threads INT
                        Number of concurrent threads to use for pulling [8]
  -v, --verbose         Enable verbose logging
```

### Examples

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

API Documentation
------------------------------------------------------

### ContainerSystem
```python
ContainerSystem(self, cDir='./containers', mDir='./modulefiles', forceImage=False, prereqs='')
```

Class for managing the rgc image cache

__Parameters__

- __cDir (str)__: Path to output container directory
- __mDir (str)__: Path to output module directory
- __forceImage (bool)__: Option to force the creation of singularity images
- __prereqs (str)__: string of prerequisite modules separated by ":"

__Attributes__

- `system (str)`: Container system
- `containerDir (str)`: Path to use for containers
- `moduleDir (str)`: Path to use for module files
- `forceImage (bool)`: Force singularity image creation
- `invalid (set)`: Set of invalid urls
- `valid (set)`: Set of valid urls
- `images (dict)`: Path of singularity image or docker url after pulling
- `registry (dict)`: Registry of origin
- `progs (dict)`: Set of programs in a container
- `name_tag (dict)`: (name, tag) tuple of a URL
- `keywords (dict)`: List of keywords for a container
- `categories (dict)`: List of categories for a container
- `homepage (dict)`: Original homepage of software in container
- `description (dict)`: Description of software in container
- `full_url (dict)`: Full URL to container in registry
- `blocklist (set)`: Set of programs to be blocked from being output
- `prog_count (Counter)`: Occurance count of each program seen
- `lmod_prereqs (list)`: List of prerequisite modules

#### validateURL
```python
ContainerSystem.validateURL(self, url)
```

Adds url to the self.invalid set when a URL is invalid and
self.valid when a URL work.

__Parameters__

- __url (str)__: Image url used to pull

#### validateURLs
```python
ContainerSystem.validateURLs(self, url_list)
```

Adds url to the self.invalid set and returns False when a URL is invalid

__Parameters__

- __url_list (list)__: List of URLs to validate

__Returns__

`list`: 	list of valid urls

#### pullAll
```python
ContainerSystem.pullAll(self, url_list, n_threads)
```

Uses worker threads to concurrently pull

 - image
 - metadata
 - repository info

for a list of urls.

__Parameters__

- __url_list (list)__: List of urls to pul
- __n_threads (int)__: Number of worker threads to use

#### pull
```python
ContainerSystem.pull(self, url)
```

Uses threads to concurrently pull:

 - image
 - metadata
 - repository info

__Parameters__

- __url (str)__: Image url used to pull

#### deleteImage
```python
ContainerSystem.deleteImage(self, url)
```

Deletes a cached image

__Parameters__

- __url (str)__: Image url used to pull

#### scanAll
```python
ContainerSystem.scanAll(self)
```

Runs `self.cachProgs` on all containers concurrently with threads

#### cacheProgs
```python
ContainerSystem.cacheProgs(self, url)
```

Crawls all directories on a container's PATH and caches a list of all executable files in

 - `self.progs[url]`

and counts the global occurance of each program in

 - `self.prog_count[prog]`

__Parameters__

- __url (str)__: Image url used to pull

#### getProgs
```python
ContainerSystem.getProgs(self, url, blocklist=True)
```

Retruns a list of all programs on the path of a url that are not blocked

__Parameters__

- __url (str)__: Image url used to pull
- __blocklist (bool)__: Filter out blocked programs

__Returns__

`list`: programs on PATH in container

#### getAllProgs
```python
ContainerSystem.getAllProgs(self, url)
```

Returns a list of all programs on the path of url.

This is a shortcut for `self.getProgs(url, blaclist=False)`

__Parameters__

- __url (str)__: Image url used to pull

#### findCommon
```python
ContainerSystem.findCommon(self, p=25)
```

Creates a blocklist containing all programs that are in at least p% of the images

 - `self.blocklist[url] = set([prog, prog, ...])`

__Parameters__

- __p (int)__: Percentile of images

#### genLMOD
```python
ContainerSystem.genLMOD(self, url, pathPrefix, contact_url)
```

Generates an Lmod modulefile based on the cached container.

__Parameters__

- __url (str)__: Image url used to pull

