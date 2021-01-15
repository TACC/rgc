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
from tqdm import tqdm
from threading import Thread, current_thread
from time import sleep
logger = logging.getLogger(__name__)

try:
	from Queue import Queue
	pyv = 2
except:
	from queue import Queue
	pyv = 3

# https://github.com/tqdm/tqdm/issues/313
class TqdmHandler(logging.StreamHandler):
    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)  # , file=sys.stderr)
            self.flush()
        except (KeyboardInterrupt, SystemExit): raise
        except: self.handleError(record)

class ThreadQueue:
	def __init__(self, target, n_threads=10):
		'''
		Class for killable thread pools

		# Parameters
		target (function): Target function for threads to run
		n_threads (int): Number of worker threads to use [10]
		verbose (bool): Enables verbose logging
		'''
		# Get the log level
		self.numerical_level = logger.getEffectiveLevel()
		self.log_level = logging.getLevelName(self.numerical_level)
		# Init logger with handler for tqdm
		FORMAT = '[%(levelname)s - %(threadName)s - %(name)s.%(funcName)s] %(message)s'
		# Store handler so it can be removed
		self.handler = TqdmHandler()
		self.handler.setFormatter(logging.Formatter(FORMAT))
		logger.addHandler(self.handler)
		logger.propagate = False
		logger.debug("Finished initializing the threaded log handler for tqdm")
		self.pbar = ''
		self.n_threads = n_threads
		self.queue = Queue()
		# Spawn threads
		self.threads = [Thread(target=self.worker, args=[target]) for i in range(n_threads)]
		for t in self.threads: t.start()
		logger.debug("Spawned and started %i threads"%(n_threads))
	def __del__(self):
		logger.debug("Removing handler")
		logger.removeHandler(self.handler)
	def process_list(self, work_list):
		'''
		# Parameters
		work_list (list): List of argument lists for threads to run
		'''
		#if self.log_level != 'DEBUG':
		self.pbar = tqdm(total=len(work_list))
		try:
			for work_item in work_list:
				self.queue.put(work_item)
			logger.debug("Added %i items to the work queue"%(len(work_list)))
			while not self.queue.empty():
				sleep(0.5)
			logger.debug("Finished running work list")
			while self.pbar.n != len(work_list): sleep(0.5)
			if self.pbar:
				self.pbar.close()
				self.pbar = ''
		except KeyboardInterrupt as e:
			logger.warning("Caught KeyboardInterrupt - Killing threads")
			for t in self.threads: t.alive = False
			for t in self.threads: t.join()
			sys.exit(e)
	def join(self):
		'''
		Waits until all child threads are joined
		'''
		try:
			for t in self.threads:
				logger.debug("Added STOP")
				self.queue.put('STOP')
			for t in self.threads:
				while t.is_alive():
					t.join(0.5)
			if self.pbar:
				self.pbar.close()
				self.pbar = ''
			logger.debug("Joined all threads")
		except KeyboardInterrupt as e:
			logger.warning("Caught KeyboardInterrupt. Killing threads")
			for t in self.threads: t.alive = False
			sp.call('pkill -9f "singularity pull"', shell=True)
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
				logger.debug("Thread was killed. Stopping")
				break
			if type(args) is list or type(args) is tuple:
				logger.debug("Running %s%s"%(target.__name__, str(map(str, args))))
				target(*args)
			else:
				logger.debug("Running %s(%s)"%(target.__name__, str(args)))
				target(args)
			#if self.log_level != 'DEBUG':
			logger.debug("Finished task. Updating progress")
			self.pbar.update(1)
			self.queue.task_done()
