###############################################################################
# Author: Greg Zynda
# Last Modified: 01/15/2021
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

from rgc.ContainerSystem.url import url_parser
from rgc.ContainerSystem.cache import cache
from rgc.helpers import translate
from rgc.ThreadQueue import ThreadQueue

class validate(url_parser, cache):
	'''
	Class for validating image URLs

	# Attributes
	valid (set): Set of valid URLs
	invalid (set): Set of invalid URLs
	tag_dict (dict): Temporary cache of tags, to prevent repeated requests
	self.registry (dict): The url:registry keypair is added
	registry_exclude_re (re): Compiled regular expression of registry urls to exclude
	n_threads (int): Default number of threads used for URL validation
	'''
	registry_exclude_re = re.compile(r'(shub://|(docker://)?(ghcr\.io|docker\.pkg\.github\.com))')
	def __init__(self):
		super(validate, self).__init__()
		self.valid = set()
		self.invalid = set()
		self.tag_dict = {}
		self.registry = {}
		self.n_threads = 4
	def validateURL(self, url, include_libs=False):
		'''
		Adds url to the self.invalid set when a URL is invalid and
		self.valid when a URL work. URLs to the following registries
		will be considered invalid because they require
		authentication:

		- Singularity Hub (shub://)
		- GitHub packages (docker.pkg.github.com)
		- GitHub container registry (ghcr.io)

		By default, containers designated as libraries on bio.tools
		are excluded.

		# Parameters
		url (str): Image url used to pull
		include_libs (bool): Include containers of libraries

		# Attributes
		self.valid (set): Where valid URLs are stored
		self.invalid (set): Where invalid URLs are stored
		self.registry_exclude_re (re): Compiled regular expression of registry urls to exclude
		'''
		# Exclude registries that require authentication
		if self.registry_exclude_re.match(url):
			logger.debug("The registry for %s requires authentication and is not supported by rgc."%(url))
			self.invalid.add(url)
			return
		# Sanitize docker prefix if included
		if url not in self.sanitized_url:
			self.parseURL(url)
		name = self.name[url]
		tag = self.tag[url]
		if not tag:
			logger.warning("Excluding - No tag included in %s"%(url))
			self.invalid.add(url)
			return
		if not include_libs:
			# See if it is a bio lib
			md_url = "https://dev.bio.tools/api/tool/%s?format=json"%(name)
			try:
				resp_json = json.loads(translate(urllib2.urlopen(md_url).read()))
				types = [v for v in resp_json['toolType']]
				if types == ['Library']:
					self.invalid.add(url)
					logger.debug("Excluding %s, which is a library"%(url))
					return
			except urllib2.HTTPError:
				pass
			## Check for pypi lib
			#if name not in set(('ubuntu','singularity','bowtie','centos')):
			#	try:
			#		code = urllib2.urlopen('https://pypi.org/pypi/%s/json'%(name)).getcode()
			#		if int(code) == 200:
			#			self.invalid.add(url)
			#			logger.debug("Excluding %s, which is a pypi package"%(url))
			#			return
			#	except urllib2.HTTPError:
			#		pass
		if tag not in self._getTags(url):
			logger.warning("%s not found in %s"%(tag, self._getTags(url)))
			self.invalid.add(url)
			logger.warning("%s is an invalid URL"%(url))
		else:
			logger.debug("%s is valid"%(url))
			self.valid.add(url)
	def _getTags(self, url, remove_latest=False):
		'''
		Returns all tags for the image specified with URL

		# Parameters
		url (str): Image url used to pull
		remove_latest (bool): Removes the "latest" tag from the return set

		# Attributes
		self.tag_dict (dict): Temporary cache of tags, to prevent repeated requests: {(registry,org,name):set,}

		# Returns
		set: all tags associated with main image URL
		'''
		tag_query = {'dockerhub':('https://hub.docker.com/v2/repositories/%s/%s/tags/','results'),\
			'quay':('https://quay.io/api/v1/repository/%s/%s/tag/','tags')} #{registry:(url,key),}
		tag_tuple = self._getUrlTuple(url)
		if self.registry[url] not in tag_query:
			logger.error('Unable to query tags for %s'%(url))
			self.tag_dict[tag_tuple] = set()
		if tag_tuple not in self.tag_dict:
			query, key = tag_query[self.registry[url]]
			query = query%(self.org[url], self.name[url])
			try:
				resp = json.loads(translate(urllib2.urlopen(query).read()))
				results = resp[key]
				while 'next' in resp and resp['next']:
					resp = json.loads(translate(urllib2.urlopen(resp['next']).read()))
					results += resp[key]
				all_tags = set([t['name'] for t in results])
				self.tag_dict[tag_tuple] = all_tags
			except urllib2.HTTPError:
				logger.warning("No response from %s"%(query))
				self.tag_dict[tag_tuple] = set()
		if not remove_latest:
			return self.tag_dict[tag_tuple]
		logger.debug("Removing the latest tag from %s"%(url))
		return self.tag_dict[tag_tuple]-set(['latest'])
	def _getUrlTuple(self, url):
		'''
		Returns all tags for the image specified with URL

		# Parameters
		url (str): Image url used to pull

		# Returns
		tuple: tag_tuple used as key of `tag_dict`
		'''
		if url not in self.registry:
			self.parseURL(url)
		return (self.registry[url], self.org[url], self.name[url])
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
		# Parse restored URLs
		for url in self.invalid | self.valid:
			logger.debug("Restored %s"%(url))
			if url not in self.registry: self.parseURL(url)
		cached = self.invalid | self.valid
		to_check = set(url_list) - cached
		if to_check:
			if not include_libs:
				logger.info("Validating all %i URLs and excluding libraries when possible using %i threads"%(len(to_check), self.n_threads))
			else:
				logger.info("Validating all %i URLs using %i threads"%(len(to_check), self.n_threads))
			# Process using ThreadQueue
			tq = ThreadQueue(target=self.validateURL, n_threads=self.n_threads)
			tq.process_list([(url, include_libs) for url in to_check])
			tq.join()
		# Write to cache
		self._cache_save(cache_file, (self.invalid, self.valid))
