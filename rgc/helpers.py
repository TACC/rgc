#!/usr/bin/env python
#
###############################################################################
# Author: Greg Zynda
# Last Modified: 08/10/2020
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

import logging, os, sys
import subprocess as sp

###### globals ############
pyv = sys.version_info.major
logger = logging.getLogger(__name__)

def retry_call(cmd, url, times=3, sleep_time=2):
	'''
	Retries the check_call command

	# Parameters
	cmd (str): Command to run
	url (str): Image url used to pull
	times (int): Number of retries allowed

	# Returns
	bool: Whether the command succeeded or not
	'''
	logger.debug("Running: "+cmd)
	FNULL = open(os.devnull, 'w')
	for i in range(times):
		try:
			sp.check_call(cmd, shell=True, stdout=FNULL, stderr=FNULL)
		except KeyboardInterrupt as e:
			FNULL.close()
			sys.exit()
		except sp.CalledProcessError:
			if i < times-1:
				logger.debug("Attempting to pull %s again"%(url))
				sleep(sleep_time)
				continue
			else:
				FNULL.close()
				return False
		break
	FNULL.close()
	return True

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

def iterdict(D):
	'''
	Helper function to handle the lack of iteritems in python3

	# Parameters
	D (dict): target dictionary to iterate over

	# Returns
	iterator: iterator of (key, value) pairs
	'''
	try:
		# Python 2
		OI = D.iteritems()
	except:
		# Python 3
		OI = D.items()
	return OI
