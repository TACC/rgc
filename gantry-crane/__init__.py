#!/usr/bin/env python
#
###############################################################################
# Author: Greg Zynda
# Last Modified: 11/16/2018
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
from collections import Counter
try: import urllib2
except: import urllib.request as urllib2
from threading import Thread

def ee(code, msg):
	sys.stderr.write(msg+'\n')
	sys.exit(code)
# Environment
FORMAT = "[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)15s] %(message)s"

def main():
	parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description='''\
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

''')
	parser.add_argument('-I', '--imgdir', metavar='PATH', \
		help='Directory used to cache singularity images [%(default)s]', \
		default='./containers', type=str)
	parser.add_argument('-M', '--moddir', metavar='PATH', \
		help='Path to modulefiles [%(default)s]', default='./modulefiles', type=str)
	parser.add_argument('-P', '--prefix', metavar='STR', \
		help='Prefix string to image directory for when an environment variable is used - not used by default', \
		default='', type=str)
	parser.add_argument('-p', '--percentile', metavar='INT', \
		help='Remove packages that [%(default)s]', default='25', type=str)
	parser.add_argument('-S', '--singularity', action='store_true', \
		help='Images are cached as singularity containers - even when docker is present')
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
		forceImage=args.singularity)
	################################
	# Pull default images
	################################
	defaultURLS = ['ubuntu:xenial', 'centos:7', 'ubuntu:bionic', 'continuumio/miniconda:latest', 'biocontainers/biocontainers:latest']
	logger.debug("Pulling default images for baeline PATHs")
	for url in defaultURLS: cSystem.pull(url)
	logger.debug("DONE pulling default images")
	################################
	# Pull and process specified images
	################################
	logger.debug("Pulling specified images")
	for url in args.urls: cSystem.pull(url)
	logger.debug("Scanning pulled images")
	cSystem.scanAll()
	logger.debug("Blacklisting programs in at least %i%% of images"%(args.percentile))
	cSystem.findCommon(p=args.percentile)
	################################
	# Generate module files
	################################
	logger.debug("Creating Lmod files")
	for url in urls: cSystem.genLMOD(url)
	logger.info("Finished creating Lmod files for all %i containers"%(len(args.urls)))

class ContainerSystem:
	def __init__(self, cDir, mDir, forceImage):
		self.system = self.detectSystem()
		self.containerDir = cDir
		self.moduleDir = mDir
		self.forceImage = forceImage
		if self.system == 'singularity' or forceImage:
			logger.debug("Creating %s for caching images"%(cDir))
			os.makedirs(cDir)
		logger.debug("Creating %s for modulefiles"%(mDir))
		os.makedirs(mDir)
		self.invalid = {}
		self.images = {}
		self.registry = {}
		self.progs = {}
		self.name_tag = {}
		self.keywords = {}
		self.categories = {}
		self.homepage = {}
		self.description = {}
		self.full_url = {}
		self.blacklist = set([])
		self.prog_count = Counter()
	def detectSystem(self):
		if not sp.call('docker info &>/dev/null', shell=True):
			logger.debug("Detected docker for container management")
			return 'docker'
		elif not sp.call('singularity help &>/dev/null', shell=True):
			logger.debug("Detected singularity for container management")
			return 'singularity'
		else:
			logger.error("Neither docker nor singularity detected on system")
			sys.exit(101)
	def getRegistry(self, url):
		self.registry[url] = 'dockerhub'
		if 'quay' in url:
			self.registry[url] = 'quay'
	def validateURL(self, url):
		if tag not in self.getTags(url):
			self.invalid[url] = True
			return False
		self.invalid[url] = False
		return True
	def getTags(self, url):
		name = url.split(':')[0]
		if url not in self.registry: self.getRegistry(url)
		if self.registry[url] == 'quay':
			query = 'https://quay.io/api/v1/repository/%s/tag'%(name)
			key = 'tags'
		else:
			query = 'https://hub.docker.com/v2/repositories/%s/tags'%(name)
			key = 'results'
		try: resp = json.load(urllib2.urlopen(query))
		except urllib2.HTTPError: return set([])
		return set([t['name'] for t in resp[key]])
	def pull(self, url):
		threads = []
		self.getNameTag(url)
		for func in (self.pullImage, self.getMetadata, self.getFullURL):
			threads.append(Thread(target=func, args=(url,)))
			threads[-1].start()
		for t in threads: t.join()
	def getFullURL(self, url):
		name = url.split(':')[0]
		if "quay" in url:
			name = '/'.join(name.split('/')[1:])
			base = 'https://quay.io/repository/%s'
		else:
			base = 'https://hub.docker.com/r/%s'
		self.full_url[url] = base%(name)
	def getNameTag(self, url):
		'''
		Returns the container (name, tag) from a url
		'''
		tool_tag = 'latest'
		if ':' in url:
			tool_name, tool_tag = url.split(':')
			tool_name = tool_name.split('/')[-1]
		else:
			tool_name = url.split('/')[-1]
		self.name_tag[url] = (tool_name, tool_tag)
	def pullImage(self, url):
		if self.system == 'docker':
			sp.check_call('docker pull %s 1>/dev/null'%(url), shell=True)
			self.images[url] = url
		elif self.system == 'singularity':
			imgFile = sp.check_output('singularity pull docker://%s 2>/dev/null'%(url), shell=True).split('\n')[-1].split(' ')[-1]
			newName = os.path.join(self.containerDir, os.path.basename(imgFile))
			if not os.path.exists(newName):
				os.rename(imgFile, newName)
			self.images[url] = newName
		else:
			ee(102, "Unhandled system")
		print("Pulled %s"%(url))
	def delImage(self, url):
		if self.system == 'docker':
			sp.check_call('docker rmi %s 1>/dev/null'%(url), shell=True)
		elif self.system == 'singularity':
			os.remove(self.images[url])
		del self.images[url]
		print("Pulled %s"%(url))
	def getMetadata(self, url):
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
			keywords = ["Biocontainer"]
			desc = "The %s package"%(name)
		self.categories[url] = functions
		self.keywords[url] = topics
		self.description[url] = desc
	def scanAll(self):
		print("#"*50+"\nScanning programs in containers\n"+"#"*50)
		threads = []
		for url in self.images:
			self.cacheProgs(url)
			threads.append(Thread(target=self.cacheProgs, args=(url,)))
			threads[-1].start()
		for t in threads: t.join()
	def cacheProgs(self, url):
		'''
		Crawls all directories on a container's PATH and caches a list of all executable files
		'''
		if url not in self.images: self.pull(url)
		if url not in self.progs:
			findStr = 'export IFS=":"; find $PATH -maxdepth 1 \( -type l -o -type f \) -executable -exec basename {} \; | sort -u'
			if self.system == 'docker':
				progs = sp.check_output("docker run --rm -it %s bash -c '%s' 2>/dev/null"%(url, findStr), shell=True)
			elif self.system == 'singularity':
				progs = sp.check_output("singularity exec %s bash -c '%s' 2>/dev/null"%(self.images[url], findStr), shell=True)
			else:
				ee(102, "Unhandled system")
			progList = progs.decode('utf-8').split('\r\n')
			self.prog_count += Counter(progList)
			self.progs[url] = set(progList)
	def getProgs(self, url, blacklist=True):
		'''
		Retruns a list of all programs on the path of a url that are not blacklisted
		'''
		if url not in self.progs:
			self.cacheProgs(self, url)
		if blacklist:
			return list(self.progs[url]-self.blacklist)
		return list(self.progs[url])
	def getAllProgs(self, url):
		'''
		Returns a list of all programs on the path of url
		'''
		return self.getProgs(url, blacklist=False)
	def diffProgs(self, fromURL, newURL):
		'''
		Creates a list of programs on the path of newURL that do not exist in fromURL
		'''
		for url in (fromURL, newURL):
			if url not in self.progs: self.cacheProgs(url)
		return list(self.progs[newURL].difference(self.progs[fromURL]))
	def findCommon(self, p=25):
		'''
		Creates a blacklist containing all programs that are in at least p% of the images
		'''
		n_images = len(self.progs)
		n_percentile = p*n_images/100.0
		print("Cached %i images and %i unique programs"%(n_images,len(self.prog_count)))
		print("Excluding programs in >= %i%% of images"%(p))
		print("Excluding programs in >= %.2f images"%(n_percentile))
		self.blacklist = set([prog for prog, count in self.prog_count.items() if count >= n_percentile])
		print("Excluding:\n - "+'\n - '.join(sorted(list(self.blacklist))))
	def genLMOD(self, url):
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
		#####
		help_text = '''local help_message = [[
This is a module file for the container %s, which exposes the
following programs:

%s

This container was pulled from:

	%s

If you encounter issues running this container, please
submit a help ticket to the TACC life sciences department at

	https://portal.tacc.utexas.edu/tacc-consulting

If you encounter errors in %s or need help running it,
please contact the developer directly at

	%s
]]'''
		module_text = '''
help(help_message,"\n")

whatis("Name: %s")
whatis("Version: %s")
whatis("Category: %s")
whatis("Keywords: %s")
whatis("Description: %s")
whatis("URL: %s")

prereq("tacc-singularity")
'''
		full_text = help_text%(url, progStr, full_url, name, home)
		full_text += module_text%(name, tag, cats, keys, desc, full_url)
		if self.system == 'singularity':
			prefix = 'singularity exec ${BIOCONTAINER_DIR}/%s'%(img_path)
		elif self.system == 'docker':
			prefix = 'docker run --rm -it %s'%(img_path)
		else:
			ee(105, "Unhandled system")
		for prog in progList:
			bash_string = 'eval $(%s %s "$@")'%(prefix, prog)
			csh_string = 'eval `%s %s "$*"`'%(prefix, prog)
			func_string = 'set_shell_function("%s","%s","%s")\n'%(prog, bash_string, csh_string)
			full_text += func_string
		#####
		mPath = os.path.join(self.moduleDir, name)
		if not os.path.exists(mPath): os.makedirs(mPath)
		outFile = os.path.join(mPath, "%s.lua"%(tag))
		open(outFile,'w').write(full_text)

if __name__ == "__main__":
	main()
