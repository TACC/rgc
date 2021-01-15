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

import sys, os, logging
logger = logging.getLogger(__name__)

try:
	import cPickle as pickle
	logger.debug("Detected python2")
	pyv = 2
except:
	import pickle
	logger.debug("Detected python3")
	pyv = 3

class cache:
	def __init__(self):
		'''
		Class for interacting with variable cache

		# Attributes
		self.cache_dir (str): Location for metadata cache
		self.force_cache (bool): Ignore current cache
		'''
		super(cache, self).__init__()
		self.cache_dir = os.path.join(os.path.expanduser('~'),'rgc_cache')
		self.force_cache = False
	def _cache_load(self, file_name, default_values):
		'''
		Loads a pickle file and returns a tuple of values

		# Parameters
		file_name (str): Name of pickle file from `self.cache_dir` to load
		default_values (tuple): Tuple of default values to return if cache does not exist, or if `self.force_cache` is True.

		# Attributes
		self.cache_dir (str): Location for metadata cache
		self.force_cache (bool): Ignore current cache, and return default tuple

		# Returns
		tuple: Tuple of values loaded from pickle file
		'''
		cache_file = os.path.join(self.cache_dir, file_name)
		if not os.path.exists(cache_file):
			logger.debug("Cache file %s does not exist. Returning default values"%(cache_file))
			return default_values
		elif self.force_cache:
			logger.debug("Forcing a refresh of the cache. Returning default values")
			return default_values
		with open(cache_file, 'rb') as OC:
			logger.debug("Reading %s cache"%(cache_file))
			rv = pickle.load(OC)
		return rv
	def _cache_save(self, file_name, value_tuple):
		'''
		Saves a tuple of values to a pickle file

		# Parameters
		file_name (str): Name of file for storing values, which will be created in the `self.cache_dir`
		value_tuple (tuple): Tuple of values to save in the pickle file

		# Attributes
		self.cache_dir (str): Location for metadata cache
		'''
		cache_file = os.path.join(self.cache_dir, file_name)
		if not os.path.exists(self.cache_dir):
			logger.debug("Creating cache dir: %s"%(self.cache_dir))
			os.makedirs(self.cache_dir)
		with open(cache_file, 'wb') as OC:
			pickle.dump(value_tuple, OC)
			logger.debug("Updated %s cache"%(cache_file))
