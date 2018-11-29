# rgc

Rolling Gantry Crane - Pulls and converts containers to Lmod modulefiles

Author : Greg Zynda <gzynda@tacc.utexas.edu>

## ContainerSystem
```python
ContainerSystem(self, cDir, mDir, forceImage)
```

Class for managing the rgc image cache

__Parameters__

- __cDir (str) __: Path to output container directory
- __mDir (str) __: Path to output module directory
- __forceImage (bool) __: Option to force the creation of singularity images

### detectSystem
```python
ContainerSystem.detectSystem(self)
```

Detects the container system type {docker, singularity}

__Raises__

- `101 `: if neither docker or singularity is found

__Returns__

`str `: conainter system

### getRegistry
```python
ContainerSystem.getRegistry(self, url)
```

Sets self.registry[url] with the registry that tracks the URL

__Parameters__

- __url (str) __: Image url used to pull

### validateURL
```python
ContainerSystem.validateURL(self, url)
```

Addes url to the self.invalid set and returns False when a URL is invalid

__Parameters__

- __url (str) __: Image url used to pull

__Returns__

`bool `: 	url is valid

### getTags
```python
ContainerSystem.getTags(self, url)
```

Returns all tags for the image specified with URL

__Parameters__

- __url (str) __: Image url used to pull

__Returns__

`set `: all tags associated with main image URL

### pull
```python
ContainerSystem.pull(self, url)
```

Uses threads to concurrently pull:

 - image
 - metadata
 - repository info

__Parameters__

- __url (str) __: Image url used to pull

### getFullURL
```python
ContainerSystem.getFullURL(self, url)
```

Stores the web URL for viewing the specified image in `self.full_url[url]`

> NOTE: This does not validate the url

__Parameters__

- __url (str) __: Image url used to pull

### getNameTag
```python
ContainerSystem.getNameTag(self, url)
```

Stores the container (name, tag) from a url in `self.name_tag[url]`

__Parameters__

- __url (str) __: Image url used to pull

### pullImage
```python
ContainerSystem.pullImage(self, url)
```

Pulls an image using either docker or singularity and
sets

 - `self.images[url]`

as the URL or path for subsequent interactions.

> NOTE - this image must be valid

__Parameters__

- __url (str) __: Image url used to pull

### deleteImage
```python
ContainerSystem.deleteImage(self, url)
```

Deletes a cached image

__Parameters__

- __url (str) __: Image url used to pull

### getMetadata
```python
ContainerSystem.getMetadata(self, url)
```

Assuming the image is a biocontainer,

 - `self.categories[url]`
 - `self.keywords[url]`
 - `self.description[url]`

are set after querying https://dev.bio.tools

__Parameters__

- __url (str) __: Image url used to pull

### scanAll
```python
ContainerSystem.scanAll(self)
```

Runs `self.cachProgs` on all containers concurrently with threads

### cacheProgs
```python
ContainerSystem.cacheProgs(self, url)
```

Crawls all directories on a container's PATH and caches a list of all executable files in

 - `self.progs[url]`

and counts the global occurance of each program in

 - `self.prog_count[prog]`

__Parameters__

- __url (str) __: Image url used to pull

### getProgs
```python
ContainerSystem.getProgs(self, url, blacklist=True)
```

Retruns a list of all programs on the path of a url that are not blacklisted

__Parameters__

- __url (str) __: Image url used to pull
- __blacklist (bool) __: Filter out blacklisted programs

__Returns__

`list `: programs on PATH in container

### getAllProgs
```python
ContainerSystem.getAllProgs(self, url)
```

Returns a list of all programs on the path of url.

This is a shortcut for `self.getProgs(url, blaclist=False)`

__Parameters__

- __url (str) __: Image url used to pull

### findCommon
```python
ContainerSystem.findCommon(self, p=25)
```

Creates a blacklist containing all programs that are in at least p% of the images

 - `self.blacklist[url] = set([prog, prog, ...])`

__Parameters__

- __p (int) __: Percentile of images

### genLMOD
```python
ContainerSystem.genLMOD(self, url)
```

Generates an Lmod modulefile based on the cached container.

__Parameters__

- __url (str) __: Image url used to pull

