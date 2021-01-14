import sys, os, logging, json, re
import subprocess as sp
from collections import Counter
logger = logging.getLogger(__name__)

from rgc.ContainerSystem.pull import pull
from rgc.helpers import translate, iterdict, retry_call, delete
from rgc.ThreadQueue import ThreadQueue

class scan(pull):
	'''
	Class for interacting with variable cache

	# Attributes
	self.categories (dict)= {url: category list}
	self.keywords (dict)= {url: keyword list}
	self.description (dict)= {url: description}
	self.homepage (dict)= {url: homepage url}
	'''
	# Create cmd templates, which are used with template%(self.images[url], cmd)
	docker_cmd_template = "docker run --rm -t %s %s"
	singularity_cmd_template = "singularity exec %s %s"
	cmd_templates = {'docker':docker_cmd_template, 'singularity2':singularity_cmd_template, 'singularity3':singularity_cmd_template}
	# Supported shells
	supported_shells = ['busybox', 'bash', 'sh']
	find_string = {'bash':r'export IFS=":"; find $PATH -maxdepth 1 \( -type l -o -type f \) -executable -exec basename {} \; | sort -u',\
		'sh':r'export IFS=":"; for dir in $PATH; do [ -e "$dir" ] && find $dir -maxdepth 1 \( -type l -o -type f \) -perm +111 -exec basename {} \;; done | sort -u',\
		'busybox':r'export IFS=":"; for dir in $PATH; do [ -e "$dir" ] && find $dir -maxdepth 1 \( -type l -o -type f \) -perm +111 -exec basename {} \;; done | sort -u'}
	find_cmd = {'bash':"bash -c '%s' 2>/dev/null",\
		'sh':"sh -c '%s' 2>/dev/null",\
		'busybox':"sh -c '%s' 2>/dev/null"}
	# Programs always permitted
	permit_set = {'samtools','bwa','bowtie','bowtie2','java'}
	# Detected programs must be a combination of [a-zA-Z0-9_]
	prx = re.compile(r"\w+")
	def __init__(self):
		super(scan, self).__init__()
		self.programs = {}
		self.program_count = Counter()
		self.force_cache = False
		self.n_threads = 4
		# Always exclude time since it's a shell builtin
		self.block_set = set(['time'])
	def scanAll(self, url_list=[]):
		'''
		Runs `self.scanPrograms` on all containers with a thread pool
		'''
		cache_file = 'programs.pkl'
		if not self.force_cache:
			self.programs, self.program_count = self._cache_load(cache_file, (dict(), Counter()))
		to_check = self.valid | set(url_list)
		if self.force_cache:
			logger.debug("Ignoring cache and re-scanning all containers")
		else:
			to_check -= set(self.programs.keys())
		# Process using ThreadQueue
		tq = ThreadQueue(target=self.scanPrograms, n_threads=self.n_threads)
		if to_check:
			logger.info("Scanning for programs in all %i containers using %i threads"%(len(self.valid), self.n_threads))
			tq.process_list(to_check)
		tq.join()
		# Write to cache
		self._cache_save(cache_file, (self.programs, self.program_count))
	def scanPrograms(self, url, force=False):
		'''
		Crawls all directories on a container's PATH and caches a list of all executable files in

		 - `self.programs[url]`

		and counts the global occurance of each program in

		 - `self.program_count[prog]`

		# Parameters
		url (str): Image url used to pull
		force (bool): Force a re-scan and print results (for debugging only)
		'''
		if url not in self.images and url not in self.valid and url not in self.invalid:
			logger.warning("%s was not previously pulled. Trying to pull now."%(url))
			if not self.pull(url):
				logger.error("%s could not be pulled. Skipping scan for programs."%(url))
				return False
		if url in self.invalid:
			logger.debug("%s is invalid. Not scanning"%(url))
			return False
		# Return if programs are already cached and not forcing a refresh
		if not force and not self.force_cache and url in self.programs:
			logger.debug("Programs are already cached for %s"%(url))
			return True
		# Detect container shell
		shell = self._detect_shell(url)
		if not shell: return False
		# Scan
		logger.debug("Caching all programs in %s"%(url))
		# Create find string
		cmd = self.find_cmd[shell]%(self.find_string[shell])
		progList = self._ccheck_output(url, cmd)
		progList = list(filter(lambda x: len(x) > 0 and x[0] != '_' and self.prx.fullmatch(x), progList))
		if not progList:
			self.logger.error("No programs detected in %s. Marking as invalid."%(url))
			self.invalid.add(url)
			self.valid.remove(url)
			return False
		self.program_count += Counter(progList)
		self.programs[url] = set(progList)
		logger.debug("%s - %i unique programs found"%(url, len(set(progList))))
		return True
	def _ccall(self, url, cmd):
		if self.system not in self.cmd_templates:
			logger.error("%s system is unhandled"%(self.system))
			sys.exit(500)
		to_run = self.cmd_templates[self.system]%(self.images[url], cmd)
		logger.debug("Running: %s"%(to_run))
		return sp.call(to_run, shell=True)
	def _ccheck_output(self, url, cmd):
		if self.system not in self.cmd_templates:
			logger.error("%s system is unhandled"%(self.system))
			sys.exit(500)
		to_run = self.cmd_templates[self.system]%(self.images[url], cmd)
		logger.debug("Running: %s"%(to_run))
		output = sp.check_output(to_run, shell=True)
		return list(filter(lambda x: x, re.split(r'\r?\n', translate(output))))
	def _detect_shell(self, url):
		for shell in self.supported_shells:
			if not self._ccall(url, '[ -e /bin/%s ] &>/dev/null'%(shell)):
				return shell
		logger.error("Could not determine container env shell in %s"%(url))
		return False
	def getPrograms(self, url, block=True):
		'''
		Retruns a list of all programs on the path of a url that are not blocked

		# Parameters
		url (str): Image url used to pull
		block (bool): Filter out blocked programs

		# Returns
		list: programs on PATH in container
		'''
		if url in self.invalid: return []
		if url not in self.programs:
			logger.debug("Programs have not yet been cached for %s"%(url))
			self.scanPrograms(url)
		if block:
			return list(self.programs[url]-self.block_set)
		return list(self.programs[url])
	def findCommon(self, p=25, baseline=[]):
		'''
		Creates a block_set containing all programs that are in at least p% of the images

		 - `self.block_set = set([prog, prog, ...])`

		# Parameters
		p (int): Percentile of images
		baesline (list): Exclude all programs from this list of urls

		# Attributes
		permit_set (set): Set of programs that are always included when present
		block_set (set): Set of programs to be excluded
		'''
		n_images = len(self.programs)
		n_percentile = p*n_images/100.0
		logger.debug("Cached %i images and %i unique programs"%(n_images,len(self.program_count)))
		logger.info("Excluding programs in >= %i%% of images"%(p))
		logger.debug("Excluding programs in >= %.2f images"%(n_percentile))
		for url in baseline:
			if url in self.programs:
				self.block_set |= self.programs[url]
		self.block_set |= set([prog for prog, count in self.program_count.items() if count >= n_percentile])
		self.block_set -= self.permit_set
		logger.info("Excluded %i of %i programs"%(len(self.block_set), len(self.program_count)))
		logger.debug("Excluding:\n - "+'\n - '.join(sorted(list(self.block_set))))
