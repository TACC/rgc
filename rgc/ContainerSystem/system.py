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

		container systems installed and running on
		the host.

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
