import sys, os, logging, tarfile
from tempfile import mkdtemp, mkstemp
from shutil import rmtree
import subprocess as sp
from glob import glob
logger = logging.getLogger(__name__)
from rgc.ContainerSystem.validate import validate
from rgc.ContainerSystem.system import system
from rgc.ContainerSystem.cache import cache
from rgc.ContainerSystem.metadata import metadata
from rgc.helpers import translate, iterdict, retry_call, delete, remove_empty_sub_directories
from rgc.ThreadQueue import ThreadQueue

class pull(validate, system, cache, metadata):
	'''
	Class for interacting with variable cache

	# Attributes
	cache_dir (str): Location for metadata cache
	force_cache (bool): Ignore current cache
	'''
	ext_dict = {'docker':'sif', 'singularity2':'simg', 'singularity3':'sif'}
	singularity_docker_image = "quay.io/singularity/singularity:v3.6.4-slim"
	cache_docker_images = ['biocontainers/biocontainers:v1.2.0_cv1', 'biocontainers/biocontainers:vdebian-buster-backports_cv1', 'biocontainers/biocontainers:v1.1.0_cv2','biocontainers/biocontainers:v1.0.0_cv4']
	def __init__(self, cDir='./containers', cache_dir=False, target=''):
		super(pull, self).__init__()
		self.containerDir = cDir
		self.system = self._detectSystem()
		if self.system not in self.ext_dict:
			logger.error("%s is not supported for pulling images"%(self.system))
			sys.exit()
		self.layer_cache = False
		self.force_cache = False
		self.reached_pull_limit = False
		self.n_threads = 4
		self.images = {}
		# Support a custom cache directory
		if cache_dir:
			self.cache_dir = cache_dir
			if not os.path.exists(cache_dir): os.makedirs(cache_dir)
	def pullAll(self, url_list, delete_old=False, use_cache=True):
		'''
		Uses worker threads to concurrently pull

		 - image
		 - metadata
		 - repository info

		for a list of urls.

		# Parameters
		url_list (list): List of urls to pul
		delete_old (bool): Delete old images that are no longer used
		'''
		# Load cache
		cache_file = 'metadata.pkl'
		self.categories, self.keywords, self.description, self.homepage = self._cache_load(cache_file, [dict() for i in range(4)])
		if 'singularity' in self.system:
			# Create tool name directory
			for url in url_list:
				if url not in self.full_url: self.parseURL(url)
				simg_dir = os.path.join(self.containerDir, self.name[url])
				if not os.path.exists(simg_dir): os.makedirs(simg_dir)
			# Make singularity layer cache
			if use_cache: self._makeSingularityCache()
			# Process using ThreadQueue
			logger.info("Pulling %i containers on %i threads"%(len(url_list), self.n_threads))
			tq = ThreadQueue(target=self.pull, n_threads=self.n_threads)
			tq.process_list(url_list)
			tq.join()
		else:
			# Use single thread to pull with docker
			for url in url_list:
				self.pull(url)
		# Write to cache
		self._cache_save(cache_file, (self.categories, self.keywords, self.description, self.homepage))
		# Delete unused images
		if delete_old:
			logger.info("Deleting unused containers")
			if 'singularity' in self.system:
				all_files = set((os.path.join(p, f) for p, ds, fs in os.walk(self.containerDir) for f in fs))
				to_delete = all_files - set(self.images.values())
				for fpath in to_delete:
					if fpath.split('.')[-1] in self.container_exts:
						logger.info("Deleting old container %s"%(fpath))
						os.remove(fpath)
			else:
				logger.info("RGC is unable to determine which docker containers it created. Not deleting any")
		# Remove empty image directories
		remove_empty_sub_directories(self.containerDir)
	def pull(self, url):
		'''
		Pulls the following

		 - image
		 - metadata
		 - repository info

		# Parameters
		url (str): Image url used to pull

		# Returns:
		bool: Whether or not image was pulled
		'''
		if url not in self.full_url: self.parseURL(url)
		if url not in self.valid and url not in self.invalid: self.validateURL(url)
		if url in self.invalid:
			logger.debug("Not pulling. %s is an invalid URL"%(url))
			return False
		self._getMetadata(url)
		ret = self._pullImage(url)
		# Set homepage if to container url if it was not included in metadata
		if not self.homepage[url]:
			self.homepage[url] = self.full_url[url]
		return ret
	def _pullImage(self, url):
		'''
		Pulls an image using either docker or singularity and
		sets

		 - `self.images[url]`

		as the URL or path for subsequent interactions. Please
		use pull over pullImage.

		> NOTE - this image must be valid

		# Parameters
		url (str): Image url used to pull

		# Attributes
		self.containerDir (str): Directory for container

		# Returns
		bool: whether or not the pull was successful
		'''
		# Make sure image url is valid
		if url in self.invalid:
			logger.error("%s is not a valid URL")
			raise ValueError
		# Resolve paths and file names
		if url not in self.name: self.parseURL(url)
		img_dir = os.path.join(self.containerDir, self.name[url])
		abs_img_dir = os.path.abspath(img_dir)
		simg = '%s-%s.%s'%(self.name[url], self.tag[url], self.ext_dict[self.system])
		img_out = os.path.join(img_dir, simg)
		img_set = (os.path.join(img_dir, '%s-%s.%s'%(self.name[url], self.tag[url], ext)) for ext in self.ext_dict.values())
		# If working with file based containers
		if 'singularity' in self.system:
			# Check for image
			self.images[url] = self._checkForImage(url, img_set)
			if self.images[url]: return
			# Make image destination path
			if not os.path.exists(img_dir): os.makedirs(img_dir)
		# Pull the container
		if self.system == 'docker':
			self.images[url] = self._pullDocker(url, img_dir, simg)
		elif 'singularity' in self.system:
			self.images[url] = self._pullSingularity(url, img_dir, simg)
		else:
			logger.error("Unhandled system")
			raise ValueError
		if self.images[url]:
			logger.debug("Pulled %s"%(url))
		return bool(self.images[url])
	def _pullDocker(self, url, img_dir, simg):
		'''
		Uses docker to pull an image

		# Parameters
		url (str): Image url used to pull
		img_dir (str): Final directory for image file
		simg (str): Name of imae file

		# Attributes
		self.singularity_url (str): URL for pulling with singularity

		# Returns
		val: False if image could not be pulled or image destination if successful
		'''
		if self.reached_pull_limit and self.registry[url] == 'dockerhub':
			logger.debug("Pull limit already exceeded - skipping %s"%(url))
			self._pullError(url)
			return False
		tmp_log = mkstemp()[1]
		img_out = os.path.join(img_dir, simg)
		try:
			sp.check_call('docker pull %s &> %s'%(self.docker_url[url], tmp_log), shell=True)
			delete(tmp_log)
			return url
		except:
			self._pullError(url, tmp_log)
			delete(tmp_log)
			return False
	def _pullSingularity(self, url, img_dir, simg, cache_dir=False, clean=True, keep_img=True):
		'''
		Uses singularity to pull an image

		# Parameters
		url (str): Image url used to pull
		img_dir (str): Final directory for image file
		simg (str): Name of imae file
		cache_dir (bool): Directory of singularity cache (temp dir if not specified)
		clean (bool): Delete cache directory after pulling
		keep_img (bool): Delete image file after pulling

		# Attributes
		self.singularity_url (str): URL for pulling with singularity

		# Returns
		val: False if image could not be pulled or image destination if successful
		'''
		if self.reached_pull_limit and self.registry[url] == 'dockerhub':
			logger.debug("Pull limit already exceeded - skipping %s"%(url))
			self._pullError(url)
			return False
		tmp_dir = mkdtemp() if not cache_dir else cache_dir
		tmp_log = mkstemp()[1]
		img_out = os.path.join(img_dir, simg)
		logger.debug("Created temporary directory: %s"%(tmp_dir))
		if self.layer_cache:
			self._extractSingularityCache(tmp_dir)
			assert os.path.exists(os.path.join(tmp_dir,'cache'))
		try:
			# assert statments break the try section
			tmp_img_out = img_out+' ' if self.system == 'singularity3' else ''
			cmd = 'SINGULARITY_CACHEDIR=%s singularity pull -F %s%s &> %s'%(tmp_dir, tmp_img_out, self.singularity_url[url], tmp_log)
			if retry_call(cmd, url): logger.debug("Finished pulling %s"%(url))
			if self.system == 'singularity2':
				tmp_path = os.path.join(tmp_dir, simg)
				assert(os.path.exists(tmp_path))
				move(tmp_path, img_out)
			assert(os.path.exists(img_out))
		except:
			self._pullError(url)
			self._pullWarn(tmp_log)
			delete(tmp_dir, tmp_log)
			return False
		if clean: delete(tmp_dir)
		if not keep_img: delete(img_out)
		delete(tmp_log)
		return img_out
	def _extractSingularityCache(self, extract_to):
		'''
		Extracts the singularity cache to a directory.

		# Parameters
		extract_to (str): Directory cache is extracted to
		'''
		if self.layer_cache and os.path.exists(self.layer_cache):
			assert os.path.exists(extract_to)
			logger.debug("Extracting %s to %s"%(self.layer_cache, extract_to))
			with tarfile.open(self.layer_cache,'r') as TF:
				TF.extractall(extract_to)
		else:
			logger.warning("No layer cache detected")
	def _makeSingularityCache(self):
		'''
		Pulls and builds the layer cache for singularity images

		# Attributes
		self.cache_dir (str): Path to the cache directory
		self.layer_cache (str): Path to the layer cache tarball

		# Raises
		Exception: If the layer cache cannot be built
		'''
		# Cache names
		cache_folder = os.path.join(self.cache_dir, 'scache')
		cache_file = os.path.join(self.cache_dir, 'scache.tar')
		# Skip re-creating file if not being forced
		if not self.force_cache:
			if self.layer_cache and os.path.exists(self.layer_cache):
				logger.info("Using existing layer cache %s"%(self.layer_cache))
				return
			if not self.layer_cache and os.path.exists(cache_file):
				logger.info("Using found layer cache %s"%(cache_file))
				self.layer_cache = cache_file
				return
		# Create the cache directory
		if not os.path.exists(cache_folder):
			logger.debug("Making temporary cache folder: %s"%(cache_folder))
			os.makedirs(cache_folder)
		logger.warning("Creating the base layer cache. This may take a while")
		# Pull the images in parallel
		tq = ThreadQueue(target=self._pullSingularity, n_threads=self.n_threads)
		arg_list = []
		for url in self.cache_docker_images:
			self.parseURL(url)
			dir, fname = os.path.split(mkstemp()[1])
			arg_list.append((url, dir, fname, cache_folder, False, False))
		tq.process_list(arg_list)
		tq.join()
		# Delete OCI files
		delete(*glob(os.path.join(cache_folder,'cache/oci-tmp/*')))
		logger.debug("Creating TAR file %s"%(cache_file))
		with tarfile.open(cache_file,'w') as TF:
			TF.add(os.path.join(cache_folder,'cache'), arcname='cache')
		delete(cache_folder)
		self.layer_cache = cache_file
	def _pullError(self, url, log_txt=""):
		'''
		If an image URL can't be pulled, the image is marked as invalid.
		If a log file is included, a warning is thrown if the Docker Hub pull limit has ben exceeded.

		# Parameters
		url (str): Image url used to pull
		log_txt (str): Path to temprorary log file (optional)

		# Attributes
		self.valid (set): Set of valid URLs
		self.invalid (set): Set of invalid URLs
		'''
		logger.error("Could not pull %s"%(url))
		if log_txt: self._pullWarn(log_txt)
		self.invalid.add(url)
		self.valid.remove(url)
	def _pullWarn(self, log_txt):
		'''
		Issues a warning if the Docker Hub pull limit has been exceeded.

		# Parameters
		log_txt (str): Path to temprorary log file (optional)

		# Attributes
		self.reached_pull_limit (bool): Variable to ensure the warning is only issued once
		'''
		# Only warn once
		if self.reached_pull_limit: return
		if "reached your pull rate limit" in log_txt:
			logger.warning('''You have reached your pull limit on Docker Hub. You can try the following to increase it:

			1. Autenticate
			   * Singularity - https://sylabs.io/guides/3.7/user-guide/singularity_and_docker.html#authentication-via-environment-variables
			   * Docker      - https://docs.docker.com/engine/reference/commandline/login/
			2. Upgrade to a Docker Pro account
			   * https://www.docker.com/pricing
			3. Wait 6 hours for limit to refresh
			4. Change public IP

			https://docs.docker.com/docker-hub/download-rate-limit/''')
			self.reached_pull_limit = True
	def _checkForImage(self, url, img_set):
		'''
		# Parameters
		url (str): Image url used to pull
		img_set (set): Set of possible image paths to check for

		# Returns
		val: False if image not found or image destination if successful
		'''
		for img_path in img_set:
			if os.path.exists(img_path):
				logger.debug("Detected %s for url %s - using this version"%(img_path, url))
				return img_path
		return False
	def deleteImage(self, url):
		'''
		Deletes a cached image

		# Parameters
		url (str): Image url used to pull
		'''
		if url in self.images:
			if self.system == 'docker':
				sp.check_call('docker rmi %s &>/dev/null'%(url), shell=True)
			elif 'singularity' in self.system:
				os.remove(self.images[url])
				container_dir = os.path.dirname(self.images[url])
				if not os.listdir(container_dir):
					os.rmdir(container_dir)
			del self.images[url]
			self.logger.info("Deleted %s"%(url))
		else:
			self.logger.info("%s didn't exist"%(url))
