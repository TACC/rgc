rgc - Rolling Gantry Crane
======================================================

Pulls containers from either:

- docker hub
- quay.io

and generates Lmod modulefiles for us on HPC systems.

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
usage: rgc [-h] [-I PATH] [-M PATH] [-P STR] [-p INT] [-S] [-v] URL [URL ...]
 
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

#### detectSystem
```python
ContainerSystem.detectSystem(self)
```

Detects the container system type {docker, singularity}

__Raises__

- `101`: if neither docker or singularity is found

__Returns__

`str`: conainter system

#### getRegistry
```python
ContainerSystem.getRegistry(self, url)
```

Sets self.registry[url] with the registry that tracks the URL

__Parameters__

- __url (str)__: Image url used to pull

#### validateURL
```python
ContainerSystem.validateURL(self, url)
```

Addes url to the self.invalid set and returns False when a URL is invalid

__Parameters__

- __url (str)__: Image url used to pull

__Returns__

`bool`: 	url is valid

#### getTags
```python
ContainerSystem.getTags(self, url)
```

Returns all tags for the image specified with URL

__Parameters__

- __url (str)__: Image url used to pull

__Returns__

`set`: all tags associated with main image URL

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

#### getFullURL
```python
ContainerSystem.getFullURL(self, url)
```

Stores the web URL for viewing the specified image in `self.full_url[url]`

> NOTE: This does not validate the url

__Parameters__

- __url (str)__: Image url used to pull

#### getNameTag
```python
ContainerSystem.getNameTag(self, url)
```

Stores the container (name, tag) from a url in `self.name_tag[url]`

__Parameters__

- __url (str)__: Image url used to pull

#### pullImage
```python
ContainerSystem.pullImage(self, url)
```

Pulls an image using either docker or singularity and
sets

 - `self.images[url]`

as the URL or path for subsequent interactions.

> NOTE - this image must be valid

__Parameters__

- __url (str)__: Image url used to pull

#### deleteImage
```python
ContainerSystem.deleteImage(self, url)
```

Deletes a cached image

__Parameters__

- __url (str)__: Image url used to pull

#### getMetadata
```python
ContainerSystem.getMetadata(self, url)
```

Assuming the image is a biocontainer,

 - `self.categories[url]`
 - `self.keywords[url]`
 - `self.description[url]`

are set after querying https://dev.bio.tools

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
ContainerSystem.getProgs(self, url, blacklist=True)
```

Retruns a list of all programs on the path of a url that are not blacklisted

__Parameters__

- __url (str)__: Image url used to pull
- __blacklist (bool)__: Filter out blacklisted programs

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

Creates a blacklist containing all programs that are in at least p% of the images

 - `self.blacklist[url] = set([prog, prog, ...])`

__Parameters__

- __p (int)__: Percentile of images

#### genLMOD
```python
ContainerSystem.genLMOD(self, url, pathPrefix)
```

Generates an Lmod modulefile based on the cached container.

__Parameters__

- __url (str)__: Image url used to pull

