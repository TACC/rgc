import sys, os, logging
logger = logging.getLogger(__name__)
from rgc.ContainerSystem.validate import validate
from rgc.helpers import translate, iterdict, retry_call

try:
	logger.debug("Detected python2")
	pyv = 2
except:
	logger.debug("Detected python3")
	pyv = 3

class pull(validate):
	'''
	Class for interacting with variable cache

	# Attributes
	cache_dir (str): Location for metadata cache
	force_cache (bool): Ignore current cache
	'''
	ext_dict = {'docker':'sif', 'singularity2':'simg', 'singularity3':'sif'}
	singularity_docker_image = "quay.io/singularity/singularity:v3.6.4-slim"

	def __init__(self, cDir='./containers'):
		super(pull, self).__init__()
		self.containerDir = cDir

	def pull(self, url):
		'''
		Pulls the following

		 - image
		 - metadata
		 - repository info

		# Parameters
		url (str): Image url used to pull
		'''
		if url not in self.full_url: self.parseURL(url)
		if url not in self.valid and url not in self.invalid: self.validateURL(url)
		if url in self.invalid:
			logger.debug("Not pulling. %s is an invalid URL"%(url))
			return
		# URL is valid
		if url not in self.name_tag: self._getNameTag(url)
		self._getMetadata(url)
		self._pullImage(url)
		# Set homepage if to container url if it was not included in metadata
		if not self.homepage[url]:
			self.homepage[url] = self.full_url[url]
	def _pullImage(self, url, useLayerCache=True):
		'''
		Pulls an image using either docker or singularity and
		sets

		 - `self.images[url]`

		as the URL or path for subsequent interactions. Please
		use pull over pullImage.

		> NOTE - this image must be valid

		# Parameters
		url (str): Image url used to pull
		'''
		if url in self.invalid:
			logger.error("%s is not a valid URL")
			raise ValueError
		if url not in self.name: self.parseURL(url)
		# Resolve paths and file names
		img_dir = os.path.join(self.containerDir, self.name[url])
		abs_img_dir = os.path.abspath(img_dir)
		simg = '%s-%s.%s'%(name, tag, self.ext_dict[self.system])
		img_out = os.path.join(img_dir, simg)
		img_set = (os.path.join(img_dir, '%s-%s.%s'%(name, tag, ext)) for ext in ext_dict.values())
		# Pull the container
		if self.system == 'docker':
			if self.forceImage:
				if self._checkForImage(img_set): return
				if not os.path.exists(img_dir): os.makedirs(img_dir)
				cmd = "docker run -v %s:/containers --rm %s bash -c 'cd /containers && singularity pull docker://%s' &>/dev/null"%(abs_img_dir, self.singularity_docker_image, url)
				if self._retry_call(cmd, url):
					assert(os.path.exists(img_out))
					self.images[url] = img_out
				else:
					self._pullError(url)
			else:
				try:
					sp.check_call('docker pull %s &>/dev/null'%(url), shell=True)
					self.images[url] = url
				except:
					self._pullError(url)
		elif 'singularity' in self.system:
			if self._checkForImage(img_set): return
			if not os.path.exists(img_dir): os.makedirs(img_dir)
			tmp_dir = translate(sp.check_output('mktemp -d -p /tmp', shell=True)).rstrip('\n')
			try:
				if self.system == 'singularity2':
					cmd = 'SINGULARITY_CACHEDIR=%s singularity pull -F docker://%s &>/dev/null'%(tmp_dir, url)
					self._retry_call(cmd, url)
					tmp_path = os.path.join(tmp_dir, simg)
					assert(os.path.exists(tmp_path))
					move(tmp_path, img_out)
				elif self.system == 'singularity3':
					cmd = 'SINGULARITY_CACHEDIR=%s singularity pull -F %s docker://%s &>/dev/null'%(tmp_dir, img_out, url)
					self._retry_call(cmd, url)
					assert(os.path.exists(img_out))
				else:
					self.logger.error("Unhandled version of singularity")
					sys.exit()
			except:
				self._pullError(url)
			if os.path.exists(tmp_dir):
				sp.check_call('rm -rf %s'%(tmp_dir), shell=True)
				self.logger.debug("Deleted %s"%(tmp_dir))
			self.images[url] = img_out
		else:
			self.logger.error("Unhandled system")
			sys.exit(102)
		self.logger.debug("Pulled %s"%(url))
	def _pullError(self, url):
		logger.error("Could not pull %s"%(url))
		self.invalid.add(url)
		self.valid.remove(url)
	def _checkForImage(self, img_set):
		for p in img_set:
			if os.path.exists(p):
				logger.debug("Detected %s for url %s - using this version"%(p, url))
				self.images[url] = p
				return True
		return False
