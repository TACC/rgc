import sys, os, logging, re, json
logger = logging.getLogger(__name__)

try:
	logger.debug("Detected python2")
	import urllib2
	pyv = 2
except:
	logger.debug("Detected python3")
	import urllib.request as urllib2
	pyv = 3

from rgc.helpers import translate, iterdict

class url_parser:
	'''
	Class for santizing input URLs

	# Attributes
	known_registries (dict): Static dictionary of known registries {name:identifier,}
	full_url_templates (dict): Static dictionary of full_url templates {name:template,}
	'''
	known_registries = {'dockerhub':'dockerhub','quay':'quay',\
		'github':'github','ghcr':'ghcr','shub':'shub'}
	full_url_templates = {'dockerhub':'https://hub.docker.com/r/%s/%s',\
		'quay':'https://quay.io/repository/%s/%s',\
		'github':'https://docker.pkg.github.com/%s/%s',\
		'ghcr':'https://ghcr.io/%s/%s',\
		'shub':'https://singularity-hub.org/%s/%s'}
	def __init__(self):
		'''
		Sets the following attributes at initialization.

		# Attributes
		self.sanitized_url (dict): Dictionary of {url:"sanitized url",} pairs
		self.org (dict): Dictionary of url:"image org" pairs
		self.name (dict): Dictionary of url:"image name" pairs
		self.tag (dict): Dictionary of url:"image tag" pairs
		self.registry (dict): The url:registry keypair is added
		self.full_url (dict): Dictionary of full-length URLs for requested image URL
		'''
		super(url_parser, self).__init__()
		self.sanitized_url = {}
		self.org = {}
		self.name = {}
		self.tag = {}
		self.registry = {}
		self.full_url = {}
	def parseURL(self, url):
		'''
		Sanitizes and identifies the image name, tag, and registry of a given URL

		# Parameters
		url (str): Image URL used to pull image
		'''
		self._sanitize(url)
		self._split(url)
		self._detectRegistry(url)
		self._fullURL(url)
	def sanitize(self, url):
		'''
		Sanitizes and returns the base URL

		# Parameters
		url (str): Image URL used to pull image

		# Returns
		str: Sanitized URL
		'''
		self._sanitize(url)
		return self.sanitized_url[url]
	def _sanitize(self, url):
		'''
		Sanitizes and returns the base URL

		# Attributes
		self.sanitized_url (dict): Dictionary of {url:"sanitized url",} pairs

		# Parameters
		url (str): Image URL used to pull image
		'''
		self.sanitized_url[url] = url.replace('docker://','',1).replace('shub://','',1)
	def _fullURL(self, url):
		'''
		Stores the web URL for viewing the specified image in `self.full_url[url]`

		> NOTE: This does not validate the url

		# Parameters
		url (str): Image url used to pull

		# Attributes
		self.full_url (dict): Dictionary of full-length URLs for requested image URL
		self.full_url_templates (dict): Static dictionary of full_url templates {name:template,}
		'''
		if url not in self.registry: self._detectRegistry(url)
		if url not in self.org: self._split(url)
		template = self.full_url_templates[self.registry[url]]
		self.full_url[url] = template%(self.org[url], self.name[url])
	def _split(self, url):
		'''
		Splits the image name and tag from the sanitized URL.

		# Attributes
		self.sanitized_url (dict): {url:sanitized_url,}
		self.org (dict): {url:org,} The org of the URL
		self.name (dict): {url:name,} The org/user is dropped from the URL
		self.tag (dict): {url:tag,} If no tag is detected, a warning is thrown and value is set to `False`

		# Parameters
		url (str): Image url used to pull
		'''
		# Split name and tag
		if url not in self.sanitized_url: self._sanitize(url)
		san_url = self.sanitized_url[url]
		image_tag = san_url.split('/')[-1]
		org = san_url.split('/')[-2] if '/' in san_url else 'library'
		if ':' in image_tag:
			name, tag = image_tag.split(':')
		else:
			logger.warning("No tag was given for %s"%(url))
			name = image_tag
			tag = False
		self.org[url] = org
		self.name[url] = name
		self.tag[url] = tag
	def _detectRegistry(self, url):
		'''
		Sets self.registry[url] with the registry that tracks the URL.
		This will work on invalid URLs.

		# Attributes
		self.registry (dict): The url:registry keypair is added
		self.known_registries (dict): A "identifying keword":"registry name" dictionary

		# Parameters
		url (str): Image url used to pull
		'''
		self.registry[url] = 'dockerhub'
		for k,v in iterdict(self.known_registries):
			if k in url:
				self.registry[url] = v
				break
		logger.debug("URL %s associated with %s registry"%(url, self.registry[url]))
	def getRegistry(self, url):
		'''
		Sets self.registry[url] with the registry that tracks the URL.
		This will work on invalid URLs.

		# Attributes
		self.registry (dict): The url:registry keypair is added

		# Parameters
		url (str): Image url used to pull

		# Returns
		str: The detected registry
		'''
		try:
			return self.registry[url]
		except:
			self._detectRegistry(url)
			return self.registry[url]