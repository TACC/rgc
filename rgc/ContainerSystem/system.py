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
import subprocess as sp

from rgc.helpers import translate

class system:
	def __init__(self):
		super(system, self).__init__()
		self.system = None
		self.target_systems = {'docker':self._detectDocker, 'singularity':self._detectSingularity}
	def _detectSystem(self, target=''):
		'''
		Looks for container systems in the following order

		 1. docker
		 2. singularity

		container systems installed and running on the host.

		# Parameters
		target (str): Target either docker or singularity container system

		# Raises
		SystemError: If neither docker nor singularity is found
		ValueError: If target specified but not found

		# Returns
		str: conainter system
		'''
		if target:
			if target not in self.target_systems:
				logger.error("%s is not a valid target system"%(target))
				raise ValueError
			ret_ts = self.target_systems[target]()
			if ret_ts:
				return ret_ts
			else:
				logger.error("Did not detect target system: %s"%(target))
				raise ValueError
		# Check for docker
		dd = self._detectDocker()
		if dd: return dd
		# Check for singularity
		ds = self._detectSingularity()
		if ds: return ds
		# No container system detected
		logger.error("No supported container system detected on system")
		raise SystemError
	def _detectDocker(self):
		if not sp.call('which docker &>/dev/null', shell=True):
			logger.debug("Detected docker on the system PATH")
			if not sp.call('docker info &>/dev/null', shell=True):
				logger.debug("Detected docker for container management")
				return 'docker'
			logger.warning("Does docker need to be activated or run with sudo?")
		return False
	def _detectSingularity(self):
		if not sp.call('singularity help &>/dev/null', shell=True):
			logger.debug("Detected singularity for container management")
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
			logger.debug("Detected singularity %c.%c"%(split_version[0], split_version[1]))
			return 'singularity%c'%(version)
		logger.debug("Did not detect singularity")
		return False
