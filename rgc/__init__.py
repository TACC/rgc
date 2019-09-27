#!/usr/bin/env python
#
###############################################################################
# Author: Greg Zynda
# Last Modified: 09/17/2019
###############################################################################
# BSD 3-Clause License
# 
# Copyright (c) 2018, Texas Advanced Computing Center - UT Austin
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
# 
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
# 
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
###############################################################################

import subprocess as sp
import sys, argparse, os, json, logging
logger = logging.getLogger(__name__)
from collections import Counter
from threading import Thread, current_thread
from shutil import move
from tqdm import tqdm
from time import sleep
try:
	from Queue import Queue
	import urllib2
	import cPickle as pickle
	pyv = 2
except:
	from queue import Queue
	import urllib.request as urllib2
	import pickle
	pyv = 3

from .version import version as __version__

# Environment
FORMAT = "[%(levelname)s - %(funcName)s] %(message)s"

def main():
	parser = argparse.ArgumentParser(description='rgc - Pulls containers and generates Lmod modulefiles for use on HPC systems')
	parser.add_argument('-I', '--imgdir', metavar='PATH', \
		help='Directory used to cache singularity images [%(default)s]', \
		default='./containers', type=str)
	parser.add_argument('-M', '--moddir', metavar='PATH', \
		help='Path to modulefiles [%(default)s]', default='./modulefiles', type=str)
	parser.add_argument('-C', '--contact', metavar='STR', \
		help='Contact URL(s) in modules separated by "," [%(default)s]', default='https://github.com/TACC/rgc/issues', type=str)
	parser.add_argument('-P', '--prefix', metavar='STR', \
		help='Prefix string to image directory for when an environment variable is used - not used by default', \
		default='', type=str)
	parser.add_argument('-r', '--requires', metavar='STR', \
		help='Module prerequisites separated by "," [%(default)s]', default='', type=str)
	parser.add_argument('--modprefix', metavar='STR', \
		help='Prefix for all module names bwa/1.12 -> bwa/[prefix]-1.12', \
		default='', type=str)
	parser.add_argument('--cachedir', metavar='STR', \
		help='Directory to cache metadata in [~/rgc_cache]', \
		default=os.path.join(os.path.expanduser('~'),'rgc_cache'), type=str)
	parser.add_argument('-L', '--include-libs', action='store_true', help='Include containers of libraries')
	parser.add_argument('-p', '--percentile', metavar='INT', \
		help='Exclude programs in >= p%% of images [%(default)s]', default='25', type=int)
	parser.add_argument('-S', '--singularity', action='store_true', \
		help='Images are cached as singularity containers - even when docker is present')
	parser.add_argument('-f', '--force', action='store_true', \
		help='Force overwrite the cache')
	parser.add_argument('-d', '--delete-old', action='store_true', \
		help='Delete unused containers and module files')
	parser.add_argument('-t', '--threads', metavar='INT', \
		help='Number of concurrent threads to use for pulling [%(default)s]', default='8', type=int)
	parser.add_argument('--version', action='version', version='%(prog)s {version}'.format(version=__version__))
	parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
	parser.add_argument('urls', metavar='URL', type=str, nargs='+', help='Image urls to pull')
	args = parser.parse_args()
	################################
	# Configure logging
	################################
	if args.verbose:
		logging.basicConfig(level=logging.DEBUG, format=FORMAT)
	else:
		logging.basicConfig(level=logging.INFO, format=FORMAT)
	logger = logging.getLogger(__name__)
	if args.verbose: logger.debug("DEBUG logging enabled")
	################################
	# Create container system
	################################
	cSystem = ContainerSystem(cDir=args.imgdir, mDir=args.moddir, \
		forceImage=args.singularity, prereqs=args.requires, \
		threads=args.threads, verbose=args.verbose)
	logger.info("Finished initializing system")
	################################
	# Define default URLs
	################################
	defaultURLS = ['ubuntu:xenial', 'centos:7', 'ubuntu:bionic', 'continuumio/miniconda:latest', 'biocontainers/biocontainers:latest','gzynda/build-essential:bionic']
	################################
	# Validate all URLs
	################################
	cSystem.validateURLs(defaultURLS+args.urls, args.include_libs)
	logger.debug("DONE validating URLs")
	################################
	# Pull all URLs
	################################
	cSystem.pullAll(defaultURLS+args.urls, args.delete_old)
	logger.debug("DONE pulling all urls")
	################################
	# Process all images
	################################
	logger.debug("Scanning all images")
	cSystem.scanAll()
	cSystem.findCommon(p=args.percentile, baseline=defaultURLS)
	logger.debug("DONE scanning images")
	################################
	# Delete default images
	################################
	for url in defaultURLS: cSystem.deleteImage(url)
	################################
	# Generate module files
	################################
	cSystem.genModFiles(args.prefix, args.contact, args.modprefix, args.delete_old)
	logger.debug("DONE creating Lmod files for all %i containers"%(len(args.urls)))

class ContainerSystem:
	'''
	Class for managing the rgc image cache
		
	# Parameters
	cDir (str): Path to output container directory
	mDir (str): Path to output module directory
	forceImage (bool): Option to force the creation of singularity images
	prereqs (str): string of prerequisite modules separated by ":"
	threads (int): Number of threads to use for concurrent operations
	cache_dir (str): Path to rgc cache
	force_cache (bool): Whether to force overwrite the cache
	verbose (bool): Whether to enable verbose logging
	
	# Attributes
	system (str): Container system
	containerDir (str): Path to use for containers
	moduleDir (str): Path to use for module files
	forceImage (bool): Force singularity image creation
	invalid (set): Set of invalid urls
	valid (set): Set of valid urls
	images (dict): Path of singularity image or docker url after pulling
	registry (dict): Registry of origin
	progs (dict): Set of programs in a container
	name_tag (dict): (name, tag) tuple of a URL
	keywords (dict): List of keywords for a container
	categories (dict): List of categories for a container
	homepage (dict): Original homepage of software in container
	description (dict): Description of software in container
	full_url (dict): Full URL to container in registry
	blocklist (set): Set of programs to be blocked from being output
	prog_count (Counter): Occurance count of each program seen
	lmod_prereqs (list): List of prerequisite modules
	n_threads (int): Number of threads to use for concurrent operations
	logger (logging): Class level logger
	cache_dir (str): Location for metadata cache
	force_cache (str): Force the regeneration of the metadata cache
	'''
	def __init__(self, cDir='./containers', mDir='./modulefiles', \
		forceImage=False, prereqs='', threads=8, \
		cache_dir=os.path.join(os.path.expanduser('~'),'rgc_cache'), \
		force_cache=False, verbose=False):
		'''
		ContainerSystem initializer
		'''
		# Init logger
		FORMAT = "[%(levelname)s - %(funcName)s] %(message)s"
		if verbose:
			logging.basicConfig(level=logging.DEBUG, format=FORMAT)
		else:
			logging.basicConfig(level=logging.INFO, format=FORMAT)
		self.logger = logging.getLogger(__name__)
		self.system = self._detectSystem()
		self.logger.debug("Using %s as the container system"%(self.system))
		self.containerDir = cDir
		self.logger.debug("Image files will be stored in %s"%(cDir))
		self.moduleDir = mDir
		self.logger.debug("Module files will be stored in %s"%(mDir))
		self.forceImage = forceImage
		if forceImage: logger.debug("Singularity images will be generated even when using docker")
		if 'singularity' in self.system or forceImage:
			self.logger.debug("Creating %s for caching images"%(cDir))
			if not os.path.exists(cDir): os.makedirs(cDir)
		if not os.path.exists(mDir):
			self.logger.debug("Creating %s for modulefiles"%(mDir))
			os.makedirs(mDir)
		self.invalid = set([])
		self.valid = set([])
		self.images = {}
		self.registry = {}
		self.progs = {}
		self.prog_count = Counter()
		self.name_tag = {}
		self.keywords = {}
		self.categories = {}
		self.homepage = {}
		self.description = {}
		self.full_url = {}
		self.blocklist = set([])
		self.lmod_prereqs = prereqs.split(',')
		self.logger.debug("Adding the following prereqs to the module files:\n - %s"%('\n - '.join(self.lmod_prereqs)))
		self.log_level = logging.getLevelName(logger.getEffectiveLevel())
		self.n_threads = threads
		self.logger.debug("Asynchronous operations will use %i threads"%(threads))
		self.cache_dir = cache_dir
		self.force_cache = force_cache
		self.container_exts = set(('simg','sif'))
	def _detectSystem(self):
		'''
		Looks for

		 1. docker
		 2. singularity

		container systems installed and running on
		the host.

		# Raises
		101: if neither docker or singularity is found

		# Returns
		str: conainter system
		'''
		if not sp.call('docker info &>/dev/null', shell=True):
			self.logger.debug("Detected docker for container management")
			return 'docker'
		elif not sp.call('singularity help &>/dev/null', shell=True):
			self.logger.debug("Detected singularity for container management")
			#singularity version 3.3.0-1.fc29
			#2.6.0-dist
			sing_version = translate(sp.check_output('singularity --version', shell=True)).rstrip('\n').split()
			if len(sing_version) > 1:
				sing_version = sing_version[2]
			else:
				sing_version = sing_version[0]
			split_version = sing_version.split('.')
			version = split_version[0]
			self.point_version = split_version[1]
			self.logger.debug("Detected singularity %c.%c"%(split_version[0], split_version[1]))
			return 'singularity%c'%(version)
		else:
			self.logger.error("Neither docker nor singularity detected on system")
			sys.exit(101)
	def _getRegistry(self, url):
		'''
		Sets self.registry[url] with the registry that tracks the URL

		# Parameters
		url (str): Image url used to pull
		'''
		self.registry[url] = 'dockerhub'
		if 'quay' in url:
			self.registry[url] = 'quay'
	def validateURL(self, url, include_libs=False):
		'''
		Adds url to the self.invalid set when a URL is invalid and
		self.valid when a URL work.

		By default, containers designated as libraries on bio.tools
		are excluded.
		
		# Parameters
		url (str): Image url used to pull
		include_libs (bool): Include containers of libraries

		# Attributes
		self.valid (set): Where valid URLs are stored
		self.invalid (set): Where invalid URLs are stored
		'''
		name, tag = url.split('/')[-1].split(':')
		if not include_libs:
			# See if it is a bio lib
			md_url = "https://dev.bio.tools/api/tool/%s?format=json"%(name)
			try:
				resp_json = json.loads(translate(urllib2.urlopen(md_url).read()))
				types = [v for v in resp_json['toolType']]
				if types == ['Library']:
					self.invalid.add(url)
					self.logger.debug("Excluding %s, which is a library"%(url))
					return
			except urllib2.HTTPError:
				pass
			## Check for pypi lib
			#if name not in set(('ubuntu','singularity','bowtie','centos')):
			#	try:
			#		code = urllib2.urlopen('https://pypi.org/pypi/%s/json'%(name)).getcode()
			#		if int(code) == 200:
			#			self.invalid.add(url)
			#			self.logger.debug("Excluding %s, which is a pypi package"%(url))
			#			return
			#	except urllib2.HTTPError:
			#		pass
		if tag not in self._getTags(url):
			self.logger.warning("%s not found in %s"%(tag, self._getTags(url)))
			self.invalid.add(url)
			self.logger.warning("%s is an invalid URL"%(url))
		else:
			self.logger.debug("%s is valid"%(url))
			self.valid.add(url)
	def _cache_load(self, file_name, default_values):
		cache_file = os.path.join(self.cache_dir, file_name)
		if not os.path.exists(cache_file) or self.force_cache:
			self.logger.debug("Refreshing %s cache"%(cache_file))
			return default_values
		with open(cache_file, 'rb') as OC:
			self.logger.debug("Reading %s cache"%(cache_file))
			rv = pickle.load(OC)
		return rv
	def _cache_save(self, file_name, value_tuple):
		cache_file = os.path.join(self.cache_dir, file_name)
		if not os.path.exists(self.cache_dir):
			os.makedirs(self.cache_dir)
		with open(cache_file, 'wb') as OC:
			pickle.dump(value_tuple, OC)
			self.logger.debug("Updated %s cache"%(cache_file))
	def validateURLs(self, url_list, include_libs=False):
		'''
		Adds url to the self.invalid set and returns False when a URL is invalid
		
		# Parameters
		url_list (list): List of URLs to validate
		include_libs (bool): Include containers of libraries
		'''
		# Start from cache
		cache_file = 'valid.pkl'
		self.invalid, self.valid = self._cache_load(cache_file, (set(), set()))
		cached = self.invalid | self.valid
		to_check = set(url_list) - cached
		if not include_libs: self.logger.info("Validating all URLs and excluding libraries when possible")
		# Process using ThreadQueue
		if self.log_level == 'DEBUG':	
			tq = ThreadQueue(target=self.validateURL, n_threads=self.n_threads, verbose=True)
		else:
			tq = ThreadQueue(target=self.validateURL, n_threads=self.n_threads, verbose=False)
		if to_check:
			self.logger.info("Validating all %i URLs using %i threads"%(len(to_check), self.n_threads))
			tq.process_list([(url, include_libs) for url in to_check])
		tq.join()
		# Write to cache
		self._cache_save(cache_file, (self.invalid, self.valid))
	def _getTags(self, url, remove_latest=False):
		'''
		Returns all tags for the image specified with URL
		
		# Parameters
		url (str): Image url used to pull
		remove_latest (bool): Removes the "latest" tag from the return set
		
		# Returns
		set: all tags associated with main image URL
		'''
		name = url.split(':')[0]
		if '/' not in name: name = 'library/'+name
		if url not in self.registry: self._getRegistry(url)
		if self.registry[url] == 'quay':
			name = '/'.join(name.split('/')[1:])
			query = 'https://quay.io/api/v1/repository/%s/tag/'%(name)
			key = 'tags'
		else:
			query = 'https://hub.docker.com/v2/repositories/%s/tags/'%(name)
			key = 'results'
		try:
			resp = json.loads(translate(urllib2.urlopen(query).read()))
			results = resp[key]
			while 'next' in resp and resp['next']:
				resp = json.loads(translate(urllib2.urlopen(resp['next']).read()))
				results += resp[key]
		except urllib2.HTTPError:
			self.logger.debug("No response from %s"%(query))
			return set([])
		all_tags = set([t['name'] for t in results])
		if not all_tags: return set([])
		max_len = max(map(len, all_tags))
		tag_str = '%%%is'%(max_len)
		debug_str = ', '.join(['\n'+tag_str%(tag) if (i) % 3 == 0 else tag_str%(tag) for i, tag in enumerate(all_tags)])
		if not remove_latest:
			return all_tags
		if 'latest' in all_tags:
			self.logger.debug("Removing the latest tag from %s"%(url))
		return all_tags-set(['latest'])
	def pullAll(self, url_list, delete_old=False):
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
		# Process using ThreadQueue
		if self.log_level == 'DEBUG':	
			tq = ThreadQueue(target=self.pull, n_threads=self.n_threads, verbose=True)
		else:
			tq = ThreadQueue(target=self.pull, n_threads=self.n_threads, verbose=False)
		self.logger.info("Pulling %i containers on %i threads"%(len(url_list), self.n_threads))
		for url in url_list:
			# Create name directory
			if 'singularity' in self.system or self.forceImage:
				if url not in self.name_tag: self._getNameTag(url)
				simg_dir = os.path.join(self.containerDir, self.name_tag[url][0])
				if not os.path.exists(simg_dir): os.makedirs(simg_dir)
		tq.process_list(url_list)
		tq.join()
		# Write to cache
		self._cache_save(cache_file, (self.categories, self.keywords, self.description, self.homepage))
		# Delete unused images
		if delete_old:
			self.logger.info("Deleting unused containers")
			if 'singularity' in self.system or self.forceImage:
				all_files = set((os.path.join(p, f) for p, ds, fs in os.walk(self.containerDir) for f in fs))
				to_delete = all_files - set(self.images.values())
				for fpath in to_delete:
					if fpath.split('.')[-1] in self.container_exts:
						self.logger.info("Deleting old container %s"%(fpath))
						os.remove(fpath)
			if self.system == 'docker':
				# TODO finish this section
				pass
				
	def pull(self, url):
		'''
		Pulls the following

		 - image
		 - metadata
		 - repository info

		# Parameters
		url (str): Image url used to pull
		'''
		#threads = []
		if url in self.invalid: return
		if url not in self.valid: ret = self.validateURL(url)
		if url in self.valid:
			if url not in self.name_tag: self._getNameTag(url)
			self._getMetadata(url)
			self._getFullURL(url)
			self._pullImage(url)
			# Set homepage if to container url if it was not included in metadata
			if not self.homepage[url]:
				self.homepage[url] = self.full_url[url]
		else:
			self.logger.warning("Could not find %s. Excluding it future operations"%(url))
	def _getFullURL(self, url):
		'''
		Stores the web URL for viewing the specified image in `self.full_url[url]`

		> NOTE: This does not validate the url
		
		# Parameters
		url (str): Image url used to pull
		'''
		name = url.split(':')[0]
		if "quay" in url:
			name = '/'.join(name.split('/')[1:])
			base = 'https://quay.io/repository/%s'
		else:
			base = 'https://hub.docker.com/r/%s'
		self.full_url[url] = base%(name)
	def _getNameTag(self, url):
		'''
		Stores the container (name, tag) from a url in `self.name_tag[url]`

		# Parameters
		url (str): Image url used to pull
		'''
		tool_tag = 'latest'
		if ':' in url:
			tool_name, tool_tag = url.split(':')
			tool_name = tool_name.split('/')[-1]
		else:
			tool_name = url.split('/')[-1]
		self.name_tag[url] = (tool_name, tool_tag)
	def _retry_call(self, cmd, url, times=3):
		'''
		Retries the check_call command

		# Parameters
		cmd (str): Command to run
		url (str): Image url used to pull
		times (int): Number of retries allowed

		# Returns
		bool: Whether the command succeeded or not
		'''
		self.logger.debug("Running: "+cmd)
		FNULL = open(os.devnull, 'w')
		for i in range(times):
			try:
				sp.check_call(cmd, shell=True, stdout=FNULL, stderr=FNULL)
			except KeyboardInterrupt as e:
				FNULL.close()
				sys.exit()
			except sp.CalledProcessError:
				if i < times-1:
					self.logger.debug("Attempting to pull %s again"%(url))
					sleep(2)
					continue
				else:
					FNULL.close()
					return False
			break
		return True
		FNULL.close()
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
		'''
		if url in self.invalid:
			self.logger.error("%s is not a valid URL")
			sys.exit(103)
		if url not in self.name_tag: self._getNameTag(url)
		name, tag = self.name_tag[url]
		ext_dict = {'docker':'simg', 'singularity2':'simg', 'singularity3':'sif'}
		img_dir = os.path.join(self.containerDir, name)
		abs_img_dir = img_dir if img_dir[0] == '/' else os.path.join(os.getcwd(), img_dir)
		simg = '%s-%s.%s'%(name, tag, ext_dict[self.system])
		img_out = os.path.join(img_dir, simg)
		img_set = (os.path.join(img_dir, '%s-%s.%s'%(name, tag, ext)) for ext in ext_dict.values())
			
		if self.system == 'docker':
			if self.forceImage:
				for p in img_set:
					if os.path.exists(p):
						self.logger.debug("Detected %s for url %s - using this version"%(p, url))
						self.images[url] = p
						return
				if not os.path.exists(img_dir): os.makedirs(img_dir)
				cmd = "docker run -v %s:/containers --rm gzynda/singularity:2.6.0 bash -c 'cd /containers && singularity pull docker://%s' &>/dev/null"%(abs_img_dir, url)
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
			for p in img_set:
				if os.path.exists(p):
					self.logger.debug("Dectect %s for url %s - using this version"%(p, url))
					self.images[url] = p
					return
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
		self.logger.error("Could not pull %s"%(url))
		self.invalid.add(url)
		self.valid.remove(url)
	def deleteImage(self, url):
		'''
		Deletes a cached image

		# Parameters
		url (str): Image url used to pull
		'''
		if url in self.images:
			if self.system == 'docker':
				if self.forceImage:
					os.remove(self.images[url])
				else:
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
	def _getMetadata(self, url):
		'''
		Assuming the image is a biocontainer,

		 - `self.categories[url]`
		 - `self.keywords[url]`
		 - `self.description[url]`
		 - `self.homepage[url]`

		are set after querying https://dev.bio.tools

		# Parameters
		url (str): Image url used to pull
		'''
		if url in self.description and url in self.keywords and url in self.description:
			return
		if url not in self.name_tag: self._getNameTag(url)
		name = self.name_tag[url][0]
		self.homepage[url] = False
		try:
			# Check dev.bio.tools
			md_url = "https://dev.bio.tools/api/tool/%s?format=json"%(name)
			resp_json = json.loads(translate(urllib2.urlopen(md_url).read()))
			topics = [topic['term'] for topic in resp_json['topic']]
			topics = [t for t in topics if t != 'N/A']
			functions = [o['term'] for f in resp_json['function'] for o in f['operation']]
			desc = resp_json['description']
			if 'homepage' in resp_json: self.homepage[url] = resp_json['homepage']
		except urllib2.HTTPError:
			try:
				# Check Launchpad
				md_url = "https://api.launchpad.net/devel/%s"%(name)
				resp_json = json.loads(translate(urllib2.urlopen(md_url).read()))
				desc = resp_json['description']
				self.homepage[url] = resp_json['homepage_url']
				topics = ["Biocontainer"]
				functions = ["Bioinformatics"]
			except:
				# Default values
				self.logger.debug("No record of %s on dev.bio.tools"%(name))
				functions = ["Bioinformatics"]
				topics = ["Biocontainer"]
				desc = "The %s package"%(name)
		self.categories[url] = functions
		self.keywords[url] = topics
		self.description[url] = desc
	def scanAll(self):
		'''
		Runs `self.cachProgs` on all containers concurrently with threads
		'''
		cache_file = 'programs.pkl'
		self.progs, self.prog_count = self._cache_load(cache_file, (dict(), Counter()))
		to_check = self.valid - set(self.progs.keys())
		# Process using ThreadQueue
		if self.log_level == 'DEBUG':	
			tq = ThreadQueue(target=self.cacheProgs, n_threads=self.n_threads, verbose=True)
		else:
			tq = ThreadQueue(target=self.cacheProgs, n_threads=self.n_threads, verbose=False)
		self.logger.info("Scanning for programs in all %i containers %i threads"%(len(self.valid), self.n_threads))
		if to_check:
			tq.process_list(to_check)
		tq.join()
		# Write to cache
		self._cache_save(cache_file, (self.progs, self.prog_count))
	def _callCMD(self, url, cmd):
		if self.system == 'docker':
			run = "docker run --rm -it %s %s"%(url, cmd)
		elif 'singularity' in self.system:
			run = "singularity exec %s %s"%(self.images[url], cmd)
		else:
			self.logger.error("%s system is unhandled"%(self.system))
			sys.exit(500)
		self.logger.debug("Running\n%s"%(run))
		return sp.call(run, shell=True)
	def _check_outputCMD(self, url, cmd):
		if self.system == 'docker':
			run = "docker run --rm -it %s %s"%(url, cmd)
			self.logger.debug("Running\n%s"%(run))
			out = sp.check_output(run, shell=True)
			out_split = translate(out).split('\r\n')
			return [l for l in out_split]
		elif 'singularity' in self.system:
			run = "singularity exec %s %s"%(self.images[url], cmd)
			self.logger.debug("Running\n%s"%(run))
			out = sp.check_output(run, shell=True)
			return translate(out).split('\n')
		else:
			self.logger.error("%s system is unhandled"%(self.system))
			sys.exit(500)
	def cacheProgs(self, url, force=False):
		'''
		Crawls all directories on a container's PATH and caches a list of all executable files in

		 - `self.progs[url]`
		
		and counts the global occurance of each program in

		 - `self.prog_count[prog]`

		# Parameters
		url (str): Image url used to pull
		force (bool): Force a re-scan and print results (for debugging only)
		'''
		if url in self.invalid: return
		if url not in self.images and url in self.valid:
			self.logger.debug("%s has not been pulled. Pulling now."%(url))
			self.pull(url)
		# Determine env
		if not self._callCMD(url, '[ -e /bin/busybox ] &>/dev/null'):
			shell = 'busybox'
		elif not self._callCMD(url, '[ -e /bin/bash ] &>/dev/null'):
			shell = 'bash'
		elif not self._callCMD(url, '[ -e /bin/sh ] &>/dev/null'):
			shell = 'sh'
		else:
			self.logger.error("Could not determine container env shell in %s"%(url))
			sys.exit(501)
		if url not in self.progs or force:
			self.logger.debug("Caching all programs in %s"%(url))
			# Create find string
			if shell == 'bash':
				findStr = 'export IFS=":"; find $PATH -maxdepth 1 \( -type l -o -type f \) -executable -exec basename {} \; | sort -u'
				cmd = "bash -c '%s' 2>/dev/null"%(findStr)
			elif shell in ('sh','busybox'):
				findStr = 'export IFS=":"; for dir in $PATH; do [ -e "$dir" ] && find $dir -maxdepth 1 \( -type l -o -type f \) -perm +111 -exec basename {} \;; done | sort -u'
				cmd = "sh -c '%s' 2>/dev/null"%(findStr)
			else:
				logger.error("%s shell is unhandled"%(shell))
				sys.exit(502)
			progList = self._check_outputCMD(url, cmd)
			progList = list(filter(lambda x: len(x) > 0 and x[0] != '_', progList))
			self.prog_count += Counter(progList)
			self.progs[url] = set(progList)
			logger.debug("%s - %i progs found - %i in set"%(url, len(progList), len(set(progList))))
	def getProgs(self, url, blocklist=True):
		'''
		Retruns a list of all programs on the path of a url that are not blocked

		# Parameters
		url (str): Image url used to pull
		blocklist (bool): Filter out blocked programs

		# Returns
		list: programs on PATH in container
		'''
		if url in self.invalid: return []
		if url not in self.progs:
			self.logger.debug("Programs have not yet been cached for %s"%(url))
			self.cacheProgs(self, url)
		if blocklist:
			return list(self.progs[url]-self.blocklist)
		return list(self.progs[url])
	def getAllProgs(self, url):
		'''
		Returns a list of all programs on the path of url.

		This is a shortcut for `self.getProgs(url, blaclist=False)`

		# Parameters
		url (str): Image url used to pull
		'''
		return self.getProgs(url, blocklist=False)
	def _diffProgs(self, fromURL, newURL):
		'''
		Creates a list of programs on the path of newURL that do not exist in fromURL
		'''
		for url in (fromURL, newURL):
			if url in self.invalid:
				self.logger.error("%s is an invalid URL"%(url))
				sys.exit(110)
			if url not in self.progs: self.cacheProgs(url)
		return list(self.progs[newURL].difference(self.progs[fromURL]))
	def findCommon(self, p=25, baseline=[]):
		'''
		Creates a blocklist containing all programs that are in at least p% of the images

		 - `self.blocklist[url] = set([prog, prog, ...])`

		# Parameters
		p (int): Percentile of images
		baesline (list): Exclude all programs from this list of urls

		# Attributes
		permitlist (set): Set of programs that are always included when present
		blocklist (set): Set of programs to be excluded
		'''
		n_images = len(self.progs)
		n_percentile = p*n_images/100.0
		self.logger.info("Cached %i images and %i unique programs"%(n_images,len(self.prog_count)))
		self.logger.info("Excluding programs in >= %i%% of images"%(p))
		self.logger.info("Excluding programs in >= %.2f images"%(n_percentile))
		self.blocklist = set([])
		for url in baseline:
			if url in self.progs:
				self.blocklist |= self.progs[url]
		self.permitlist = set(['R','Rscript','samtools','bwa','bowtie','bowtie2'])
		self.blocklist |= set([prog for prog, count in self.prog_count.items() if count >= n_percentile])
		self.blocklist -= self.permitlist
		self.logger.info("Excluded %i of %i programs"%(len(self.blocklist), len(self.prog_count)))
		self.logger.debug("Excluding:\n - "+'\n - '.join(sorted(list(self.blocklist))))
	def genModFiles(self, pathPrefix, contact_url, modprefix, delete_old):
		'''
		Generates an Lmod modulefile for every valid image

		# Parameters
		url (str): Image url used to pull
		pathPrefix (str): Prefix to prepend to containerDir (think environment variables)
		contact_url (list): List of contact urls for reporting issues
		modprefix (str): Container module files can be tagged with modprefix-tag for easy stratification from native modules
		delete_old (bool): Delete outdated module files
		'''
		logger.info("Creating Lmod files for specified all %i images"%(len(self.images)))
		for url in self.images:
			self.genLMOD(url, pathPrefix, contact_url, modprefix)
		if delete_old:
			# Generate all module names
			recent_modules = set([])
			for url in self.images:
				name, tag = self.name_tag[url]
				module_tag = '%s-%s'%(modprefix, tag) if modprefix else tag
				module_file = os.path.join(self.moduleDir, name, '%s.lua'%(module_tag))
				recent_modules.add(module_file)
			# Delete extras
			self.logger.info("Deleting unused module files")
			all_files = set((os.path.join(p, f) for p, ds, fs in os.walk(self.moduleDir) for f in fs))
			to_delete = all_files - recent_modules
			for fpath in to_delete:
				if fpath.split('.')[-1] == 'lua':
					self.logger.info("Deleting old container %s"%(fpath))
					os.remove(fpath)
	def genLMOD(self, url, pathPrefix, contact_url, modprefix=''):
		'''
		Generates an Lmod modulefile based on the cached container.

		# Parameters
		url (str): Image url used to pull
		pathPrefix (str): Prefix to prepend to containerDir (think environment variables)
		contact_url (list): List of contact urls for reporting issues
		modprefix (str): Container module files can be identified with modprefix-tag for easy stratification from native modules
		'''
		if url in self.invalid: return
		if url not in self.progs: self.cacheProgs(url)
		#####
		name, tag = self.name_tag[url]
		module_tag = '%s-%s'%(modprefix, tag) if modprefix else tag
		full_url = self.full_url[url]
		desc = self.description[url]
		keys = self.keywords[url]
		cats = self.categories[url]
		progList = sorted(self.getProgs(url))
		progStr = ' - '+'\n - '.join(progList)
		img_path = self.images[url].lstrip('./')
		home = self.homepage[url]
		contact_joined = '\n\t'.join(contact_url.split(','))
		#####
		if not progList:
			self.logger.error("No programs detected in %s"%(url))
			progStr = "None - please invoke manually"
		#####
		help_text = '''local help_message = [[
This is a module file for the container %s, which exposes the
following programs:

%s

This container was pulled from:

	%s

If you encounter errors in %s or need help running the
tools it contains, please contact the developer at

	%s

For errors in the container or module file, please
submit a ticket at

	%s
]]'''
		module_text = '''
help(help_message,"\\n")

whatis("Name: %s")
whatis("Version: %s")
whatis("Category: %s")
whatis("Keywords: %s")
whatis("Description: %s")
whatis("URL: %s")

'''
		full_text = help_text%(url, progStr, full_url, name, home, contact_joined)
		full_text += module_text%(name, module_tag, cats, keys, desc, full_url)
		# add prereqs
		if self.lmod_prereqs[0]: full_text += 'prereq("%s")\n'%('","'.join(self.lmod_prereqs))
		# add functions
		if 'singularity' in self.system:
			if pathPrefix:
				prefix = 'singularity exec %s'%(os.path.join(pathPrefix, img_path))
			else:
				prefix = 'singularity exec %s'%(os.path.join(os.getcwd(), img_path))
		elif self.system == 'docker':
			prefix = 'docker run --rm -it %s'%(img_path)
		else:
			self.logger.error("Unhandled system")
			sys.exit(102)
		for prog in progList:
			bash_string = '%s %s $@'%(prefix, prog)
			csh_string = '%s %s $*'%(prefix, prog)
			func_string = 'set_shell_function("%s",\'%s\',\'%s\')\n'%(prog, bash_string, csh_string)
			full_text += func_string
		#####
		mPath = os.path.join(self.moduleDir, name)
		if not os.path.exists(mPath): os.makedirs(mPath)
		outFile = os.path.join(mPath, "%s.lua"%(module_tag))
		#print(full_text.encode('utf8'))
		with open(outFile,'w') as OF: OF.write(full_text)

def _a_path_exists(path_iter):
	for p in path_iter:
		if os.path.exists(p):
			logger.debug("Previously pulled image %s exists"%(p))
			return True
	return False
	#return max(map(os.path.exists, path_iter))

def translate(s):
	if pyv == 3:
		return s.decode('utf-8')
	elif pyv == 2:
		try:
			return s.encode('ascii','ignore')
		except:
			return s.decode('utf8','ignore').encode('ascii','ignore')
	else:
		sys.exit("Python version was not detected")

class ThreadQueue:
	def __init__(self, target, n_threads=10, verbose=False):
		'''
		Class for killable thread pools
		
		# Parameters
		target (function): Target function for threads to run
		n_threads (int): Number of worker threads to use [10]
		verbose (bool): Enables verbose logging
		'''
		# Init logger
		FORMAT = '[%(levelname)s - %(threadName)s - %(name)s.%(funcName)s] %(message)s'
		if verbose:
			self.log_level = 'DEBUG'
			logging.basicConfig(level=logging.DEBUG, format=FORMAT)
		else:
			self.log_level = 'INFO'
			logging.basicConfig(level=logging.INFO, format=FORMAT)
		self.pbar = ''
		self.logger = logging.getLogger('ThreadQueue')
		self.n_threads = n_threads
		self.queue = Queue()
		# Spawn threads
		self.threads = [Thread(target=self.worker, args=[target]) for i in range(n_threads)]
		for t in self.threads: t.start()
		self.logger.debug("Spawned and started %i threads"%(n_threads))
	def process_list(self, work_list):
		'''
		# Parameters
		work_list (list): List of argument lists for threads to run
		'''
		if self.log_level != 'DEBUG': self.pbar = tqdm(total=len(work_list))
		try:
			for work_item in work_list:
				self.queue.put(work_item)
			self.logger.debug("Added %i items to the work queue"%(len(work_list)))
			while not self.queue.empty():
				sleep(0.5)
			self.logger.debug("Finished running work list")
		except KeyboardInterrupt as e:
			self.logger.warn("Caught KeyboardInterrupt - Killing threads")
			for t in self.threads: t.alive = False
			for t in self.threads: t.join()
			sys.exit(e)
	def join(self):
		'''
		Waits until all child threads are joined
		'''
		try:
			for t in self.threads: self.queue.put('STOP')
			for t in self.threads:
				while t.is_alive():
					t.join(0.5)
			if self.log_level != 'DEBUG' and self.pbar:
				self.pbar.close()
				self.pbar = ''
			self.logger.debug("Joined all threads")
		except KeyboardInterrupt as e:
			self.logger.warn("Caught KeyboardInterrupt. Killing threads")
			for t in self.threads: t.alive = False
			for t in self.threads: t.join()
			sys.exit(e)
	def worker(self, target):
		'''
		Worker for pulling images

		# Parameters
		target (function): Target function for thread to run
		'''
		t = current_thread()
		t.alive = True
		for args in iter(self.queue.get, 'STOP'):
			if not t.alive:
				self.logger.debug("Stopping")
				break
			if type(args) is list or type(args) is tuple:
				self.logger.debug("Running %s%s"%(target.__name__, str(map(str, args))))
				target(*args)
			else:
				self.logger.debug("Running %s(%s)"%(target.__name__, str(args)))
				target(args)
			if t.alive and self.log_level != 'DEBUG': self.pbar.update(1)
			self.queue.task_done()

if __name__ == "__main__":
	main()
