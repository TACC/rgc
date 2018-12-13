#!/usr/bin/env python
#
###############################################################################
# Author: Greg Zynda
# Last Modified: 12/13/2018
###############################################################################
# BSD 3-Clause License
# 
# Copyright (c) 2018, Texas Advanced Computing Center
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
from threading import Thread
from shutil import move
try:
	from Queue import Queue
except:
	from queue import Queue
try: import urllib2
except: import urllib.request as urllib2

# Environment
FORMAT = "[%(levelname)s - %(funcName)s] %(message)s"

def main():
	parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''\
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

''')
	parser.add_argument('-I', '--imgdir', metavar='PATH', \
		help='Directory used to cache singularity images [%(default)s]', \
		default='./containers', type=str)
	parser.add_argument('-M', '--moddir', metavar='PATH', \
		help='Path to modulefiles [%(default)s]', default='./modulefiles', type=str)
	parser.add_argument('-r', '--requires', metavar='STR', \
		help='Module prerequisites separated by "," [%(default)s]', default='', type=str)
	parser.add_argument('-C', '--contact', metavar='STR', \
		help='Contact URL(s) in modules separated by "," [%(default)s]', default='https://github.com/zyndagj/rgc/issues', type=str)
	parser.add_argument('-P', '--prefix', metavar='STR', \
		help='Prefix string to image directory for when an environment variable is used - not used by default', \
		default='', type=str)
	parser.add_argument('-p', '--percentile', metavar='INT', \
		help='Remove packages that [%(default)s]', default='25', type=int)
	parser.add_argument('-S', '--singularity', action='store_true', \
		help='Images are cached as singularity containers - even when docker is present')
	parser.add_argument('-t', '--threads', metavar='INT', \
		help='Number of concurrent threads to use for pulling [%(default)s]', default='8', type=int)
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
		forceImage=args.singularity, prereqs=args.requires)
	logger.info("Finished initializing system")
	################################
	# Define default URLs
	################################
	defaultURLS = ['ubuntu:xenial', 'centos:7', 'ubuntu:bionic', 'continuumio/miniconda:latest', 'biocontainers/biocontainers:latest','gzynda/singularity:2.6.0']
	################################
	# Validate all URLs
	################################
	cSystem.validateURLs(defaultURLS+args.urls)
	logger.info("DONE validating URLs")
	################################
	# Pull all URLs
	################################
	logger.info("Using %i threads to pull all urls"%(args.threads))
	cSystem.pullAll(defaultURLS+args.urls, args.threads)
	logger.debug("DONE pulling all urls")
	################################
	# Process all images
	################################
	logger.debug("Scanning all images")
	cSystem.scanAll()
	cSystem.findCommon(p=args.percentile)
	logger.debug("DONE scanning images")
	################################
	# Generate module files
	################################
	logger.INFO("Creating Lmod files for specified images")
	for url in args.urls: cSystem.genLMOD(url, args.prefix, args.contact)
	logger.info("Finished creating Lmod files for all %i containers"%(len(args.urls)))
	################################
	# Delete default images
	################################
	for url in defaultURLS: cSystem.deleteImage(url)
	

class ContainerSystem:
	'''
	Class for managing the rgc image cache
		
	# Parameters
	cDir (str): Path to output container directory
	mDir (str): Path to output module directory
	forceImage (bool): Option to force the creation of singularity images
	prereqs (str): string of prerequisite modules separated by ":"
	
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
	'''
	def __init__(self, cDir='./containers', mDir='./modulefiles', forceImage=False, prereqs=''):
		'''
		ContainerSystem initializer
		'''
		self.system = self._detectSystem()
		self.containerDir = cDir
		self.moduleDir = mDir
		self.forceImage = forceImage
		if self.system == 'singularity' or forceImage:
			logger.debug("Creating %s for caching images"%(cDir))
			if not os.path.exists(cDir): os.makedirs(cDir)
		if not os.path.exists(mDir):
			logger.debug("Creating %s for modulefiles"%(mDir))
			os.makedirs(mDir)
		self.invalid = set([])
		self.valid = set([])
		self.images = {}
		self.registry = {}
		self.progs = {}
		self.name_tag = {}
		self.keywords = {}
		self.categories = {}
		self.homepage = {}
		self.description = {}
		self.full_url = {}
		self.blocklist = set([])
		self.prog_count = Counter()
		self.lmod_prereqs = prereqs.split(':')
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
			logger.debug("Detected docker for container management")
			return 'docker'
		elif not sp.call('singularity help &>/dev/null', shell=True):
			logger.debug("Detected singularity for container management")
			return 'singularity'
		else:
			logger.error("Neither docker nor singularity detected on system")
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
	def validateURL(self, url):
		'''
		Adds url to the self.invalid set when a URL is invalid and
		self.valid when a URL work.
		
		# Parameters
		url (str): Image url used to pull
		'''
		tag = url.split(':')[1]
		if tag not in self._getTags(url):
			self.invalid.add(url)
			logger.warning("%s is an invalid URL"%(url))
		else:
			logger.debug("%s is valid"%(url))
			self.valid.add(url)
	def validateURLs(self, url_list):
		'''
		Adds url to the self.invalid set and returns False when a URL is invalid
		
		# Parameters
		url_list (list): List of URLs to validate

		# Returns
		list: 	list of valid urls
		'''
		threads = [Thread(target=self.validateURL, args=(url,)) for url in url_list]
		for t in threads: t.start()
		for t in threads: t.join()
		return list(self.valid)
	def _getTags(self, url):
		'''
		Returns all tags for the image specified with URL
		
		# Parameters
		url (str): Image url used to pull
		
		# Returns
		set: all tags associated with main image URL
		'''
		name = url.split(':')[0]
		if '/' not in name: name = 'library/'+name
		if url not in self.registry: self._getRegistry(url)
		if self.registry[url] == 'quay':
			name = '/'.join(name.split('/')[1:])
			query = 'https://quay.io/api/v1/repository/%s/tag'%(name)
			key = 'tags'
		else:
			query = 'https://hub.docker.com/v2/repositories/%s/tags'%(name)
			key = 'results'
		try:
			resp = json.load(urllib2.urlopen(query))
			results = resp[key]
			while 'next' in resp and resp['next']:
				resp = json.load(urllib2.urlopen(resp['next']))
				results += resp[key]
		except urllib2.HTTPError: return set([])
		return set([t['name'] for t in results])
	def pullAll(self, url_list, n_threads):
		'''
		Uses worker threads to concurrently pull

		 - image
		 - metadata
		 - repository info

		for a list of urls.

		# Parameters
		url_list (list): List of urls to pul
		n_threads (int): Number of worker threads to use
		'''
		self.work = Queue()
		# Spawn the workers
		workers = [Thread(target=self._worker, args=(i,)) for i in range(n_threads)]
		# Start the workers
		for worker in workers: worker.start()
		# Add work to queue
		for url in url_list:
			self.work.put(url)
		# Stop the workers
		for worker in workers: self.work.put('STOP')
		# Join the threads
		for worker in workers: worker.join()
		logger.info("Finished pulling all %i containers"%(len(url_list)))
	def _worker(self, worker_id):
		'''
		Worker for pulling images

		# Parameters
		worker_id (int): Unique integer id for worker
		'''
		for url in iter(self.work.get, 'STOP'):
			logger.debug("Worker-%i: pulling %s"%(worker_id, url))
			self.pull(url)
			self.work.task_done()
		self.work.task_done()
	def pull(self, url):
		'''
		Uses threads to concurrently pull:

		 - image
		 - metadata
		 - repository info

		# Parameters
		url (str): Image url used to pull
		'''
		threads = []
		if url in self.invalid: return
		if url not in self.valid: ret = self.validateURL(url)
		if url in self.valid:
			self._getNameTag(url)
			for func in (self._pullImage, self._getMetadata, self._getFullURL):
				threads.append(Thread(target=func, args=(url,)))
				threads[-1].start()
			for t in threads: t.join()
			# Set homepage if to container url if it was not included in metadata
			if not self.homepage[url]:
				self.homepage[url] = self.full_url[url]
		else:
			logger.warning("Could not find %s. Excluding it future operations"%(url))
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
			logger.error("%s is not a valid URL")
			sys.exit(103)
		if url not in self.name_tag: self._getNameTag(url)
		name, tag = self.name_tag[url]
		simg = '%s-%s.simg'%(name, tag)
		simg_path = os.path.join(self.containerDir, simg)
		if self.system == 'docker':
			if self.forceImage:
				if os.path.exists(simg_path):
					logger.debug("Using previously pulled version of %s"%(url))
				else:
					absPath = os.path.join(os.getcwd(), self.containerDir)
					cmd = "docker run -v %s:/containers --rm gzynda/singularity:2.6.0 bash -c 'cd /containers && singularity pull docker://%s' &>/dev/null"%(absPath, url)
					logger.debug("Running: "+cmd)
					sp.check_call(cmd, shell=True)
					assert(os.path.exists(simg_path))
					self.images[url] = simg_path
			else:
				sp.check_call('docker pull %s &>/dev/null'%(url), shell=True)
				self.images[url] = url
		elif self.system == 'singularity':
			if os.path.exists(simg_path):
				logger.debug("Using previously pulled version of %s"%(url))
			else:
				tmp_dir = sp.check_output('mktemp -d -p /tmp', shell=True)
				logger.debug("Using %s as cachedir"%(tmp_dir))
				cmd = 'SINGULARITY_CACHEDIR=%s singularity pull -F docker://%s 2>/dev/null'%(tmp_dir, url)
				output = sp.check_output(cmd, shell=True).decode('utf-8').replace('\r','').split('\n')
				output = [x for x in output if '.simg' in x]
				imgFile = output[-1].split(' ')[-1]
				if not os.path.exists(simg_path):
					move(imgFile, simg_path)
				sp.check_call('rm -rf %s'%(tmp_dir), shell=True)
				logger.debug("Deleted %s"%(tmp_dir))
			self.images[url] = newName
		else:
			logger.error("Unhandled system")
			sys.exit(102)
		logger.info("Pulled %s"%(url))
	def deleteImage(self, url):
		'''
		Deletes a cached image

		# Parameters
		url (str): Image url used to pull
		'''
		if self.system == 'docker':
			if self.forceImage:
				os.remove(self.images[url])
			else:
				sp.check_call('docker rmi %s &>/dev/null'%(url), shell=True)
		elif self.system == 'singularity':
			os.remove(self.images[url])
		del self.images[url]
		logger.info("Deleted %s"%(url))
	def _getMetadata(self, url):
		'''
		Assuming the image is a biocontainer,

		 - `self.categories[url]`
		 - `self.keywords[url]`
		 - `self.description[url]`

		are set after querying https://dev.bio.tools

		# Parameters
		url (str): Image url used to pull
		'''
		if url not in self.name_tag: self._getNameTag(url)
		name = self.name_tag[url][0]
		md_url = "https://dev.bio.tools/api/tool/%s?format=json"%(name)
		self.homepage[url] = False
		try:
			resp_json = json.loads(urllib2.urlopen(md_url).read())
			#functions = [topic['term'].encode('ascii', 'ignore') for topic in resp_json['topic']]
			#topics = [topic['term'].encode('ascii', 'ignore') for topic in resp_json['topic']]
			topics = [topic['term'] for topic in resp_json['topic']]
			topics = [t for t in topics if t != 'N/A']
			functions = [o['term'] for f in resp_json['function'] for o in f['operation']]
			desc = resp_json['description']
			if 'homepage' in resp_json: self.homepage[url] = resp_json['homepage']
		except urllib2.HTTPError:
			logger.debug("No record of %s on dev.bio.tools"%(name))
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
		logger.info("\n"+"#"*50+"\nScanning programs in containers\n"+"#"*50)
		threads = []
		for url in set(self.images.keys())-self.invalid:
			self.cacheProgs(url)
			threads.append(Thread(target=self.cacheProgs, args=(url,)))
			threads[-1].start()
		for t in threads: t.join()
	def cacheProgs(self, url):
		'''
		Crawls all directories on a container's PATH and caches a list of all executable files in

		 - `self.progs[url]`
		
		and counts the global occurance of each program in

		 - `self.prog_count[prog]`

		# Parameters
		url (str): Image url used to pull
		'''
		if url in self.invalid: return
		if url not in self.images:
			logger.debug("%s has not been pulled. Pulling now."%(url))
			self.pull(url)
		if url not in self.progs:
			logger.debug("Caching all programs in %s"%(url))
			findStr = 'export IFS=":"; find $PATH -maxdepth 1 \( -type l -o -type f \) -executable -exec basename {} \; | sort -u'
			if self.system == 'docker':
				progs = sp.check_output("docker run --rm -it %s bash -c '%s' 2>/dev/null"%(url, findStr), shell=True)
				progList = progs.decode('utf-8').split('\r\n')
			elif self.system == 'singularity':
				progs = sp.check_output("singularity exec %s bash -c '%s' 2>/dev/null"%(self.images[url], findStr), shell=True)
				progList = progs.decode('utf-8').split('\n')
			else:
				logger.error("Unhandled system")
				sys.exit(102)
			self.prog_count += Counter(progList)
			self.progs[url] = set(progList)
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
			logger.debug("Programs have not yet been cached for %s"%(url))
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
				logger.error("%s is an invalid URL"%(url))
				sys.exit(110)
			if url not in self.progs: self.cacheProgs(url)
		return list(self.progs[newURL].difference(self.progs[fromURL]))
	def findCommon(self, p=25):
		'''
		Creates a blocklist containing all programs that are in at least p% of the images

		 - `self.blocklist[url] = set([prog, prog, ...])`

		# Parameters
		p (int): Percentile of images
		'''
		n_images = len(self.progs)
		n_percentile = p*n_images/100.0
		logger.info("Cached %i images and %i unique programs"%(n_images,len(self.prog_count)))
		logger.info("Excluding programs in >= %i%% of images"%(p))
		logger.info("Excluding programs in >= %.2f images"%(n_percentile))
		self.blocklist = set([prog for prog, count in self.prog_count.items() if count >= n_percentile])
		logger.info("Excluded %i of %i programs"%(len(self.blocklist), len(self.prog_count)))
		logger.debug("Excluding:\n - "+'\n - '.join(sorted(list(self.blocklist))))
	def genLMOD(self, url, pathPrefix, contact_url):
		'''
		Generates an Lmod modulefile based on the cached container.

		# Parameters
		url (str): Image url used to pull
		'''
		if url in self.invalid: return
		if url not in self.progs: self.cacheProgs(url)
		#####
		name, tag = self.name_tag[url]
		full_url = self.full_url[url]
		desc = self.description[url]
		keys = self.keywords[url]
		cats = self.categories[url]
		progList = sorted(self.getProgs(url))
		progStr = ' - '+'\n - '.join(progList)
		img_path = self.images[url]
		home = self.homepage[url]
		contact_joined = '\n\t'.join(contact_url.split(','))
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
		full_text += module_text%(name, tag, cats, keys, desc, full_url)
		# add prereqs
		if self.lmod_prereqs[0]: full_text += 'prereq("%s")\n'%('","'.join(self.lmod_prereqs))
		# add functions
		if self.system == 'singularity':
			if pathPrefix:
				prefix = 'singularity exec %s'%(os.path.join(pathPrefix, img_path))
			else:
				prefix = 'singularity exec %s'%(os.path.join(os.getcwd(), img_path))
		elif self.system == 'docker':
			prefix = 'docker run --rm -it %s'%(img_path)
		else:
			logger.error("Unhandled system")
			sys.exit(102)
		for prog in progList:
			bash_string = '%s %s $@'%(prefix, prog)
			csh_string = '%s %s $*'%(prefix, prog)
			func_string = 'set_shell_function("%s",\'%s\',\'%s\')\n'%(prog, bash_string, csh_string)
			full_text += func_string
		#####
		mPath = os.path.join(self.moduleDir, name)
		if not os.path.exists(mPath): os.makedirs(mPath)
		outFile = os.path.join(mPath, "%s.lua"%(tag))
		with open(outFile,'w') as OF: OF.write(full_text)

if __name__ == "__main__":
	main()
