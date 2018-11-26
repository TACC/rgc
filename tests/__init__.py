#!/usr/bin/env python
#
###############################################################################
# Author: Greg Zynda
# Last Modified: 11/21/2018
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

import unittest, sys, os
from shutil import rmtree
try:
	from StringIO import StringIO
except:
	from io import StringIO
# Import path to test the CLI
try:
	from unittest.mock import patch
except:
	from mock import patch
# buffer for capturing log info
logStream = StringIO()
# Need to start logger BEFORE importing any pyPlateCalibrate code
import logging
FORMAT = "[%(levelname)s - %(filename)s:%(lineno)s - %(funcName)15s] %(message)s"
logging.basicConfig(stream=logStream, level=logging.DEBUG, format=FORMAT)
# Now import rgc
import rgc
from rgc import ContainerSystem

# Variables
outDir = "test_system"

class TestRGC(unittest.TestCase):
	def setUp(self):
		self.cDir = os.path.join(outDir, 'containers')
		self.mDir = os.path.join(outDir, 'modules')
		self.good_dh_url = 'biocontainers/samtools:v1.7.0_cv2'
		self.good_dh_progs = os.path.join(os.path.dirname(__file__), 'samtools.txt')
		self.bad_dh_url = 'biocontainers/samtools:bananas'
		self.good_quay_url = 'quay.io/biocontainers/samtools:1.9--h8ee4bcc_1'
		self.bad_quay_url = 'quay.io/biocontainers/samtools:bananas'
		self.urls = (self.good_dh_url, self.bad_dh_url, self.good_quay_url, self.bad_quay_url)
		self.good_urls = (self.good_dh_url, self.good_quay_url)
		self.bad_urls = (self.bad_dh_url, self.bad_quay_url)
	def tearDown(self):
		## Runs after every test function ##
		# Wipe log
		logStream.truncate(0)
		# Clean output directory
		if os.path.exists(outDir): rmtree(outDir)
		## Runs after every test function ##
	#def testDetectSystem(self):
	#	cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
	#	self.assertEqual(cSystem.system, "docker")
	def testGetRegistry(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		cSystem.getRegistry(self.good_dh_url)
		self.assertEqual(cSystem.registry[self.good_dh_url], 'dockerhub')
		cSystem.getRegistry(self.good_quay_url)
		self.assertEqual(cSystem.registry[self.good_quay_url], 'quay')
	def testValidReturn(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		self.assertTrue(cSystem.validateURL(self.good_dh_url))
		self.assertTrue(cSystem.validateURL(self.good_quay_url))
		self.assertFalse(cSystem.validateURL(self.bad_dh_url))
		self.assertFalse(cSystem.validateURL(self.bad_quay_url))
	def testValidSet(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		for url in self.urls: cSystem.validateURL(url)
		self.assertTrue(self.good_dh_url not in cSystem.invalid)
		self.assertTrue(self.bad_dh_url in cSystem.invalid)
		self.assertTrue(self.good_quay_url not in cSystem.invalid)
		self.assertTrue(self.bad_quay_url in cSystem.invalid)
	def testTags(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		self.assertTrue('1.2' in cSystem.getTags(self.good_dh_url))
		self.assertTrue('1.0--hdd8ed8b_2' in cSystem.getTags(self.good_quay_url))
		self.assertEqual(cSystem.getTags('biocontainers/samtoolz:1.3'), set([]))
		self.assertEqual(cSystem.getTags('quay.io/biocontainers/samtoolz:1.3'), set([]))
	def testPull(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		for url in self.urls: cSystem.pull(url)
		self.assertTrue(self.good_dh_url in cSystem.images)
		self.assertTrue(self.good_quay_url in cSystem.images)
		self.assertTrue(self.good_dh_url not in cSystem.invalid)
		self.assertTrue(self.good_quay_url not in cSystem.invalid)
		self.assertTrue(self.bad_dh_url not in cSystem.images)
		self.assertTrue(self.bad_quay_url not in cSystem.images)
		self.assertTrue(self.bad_dh_url in cSystem.invalid)
		self.assertTrue(self.bad_quay_url in cSystem.invalid)
	def testPullForce(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=True)
		for url in self.urls: cSystem.pull(url)
		output = logStream.getvalue()
		print(output)
		for url in self.good_urls:
			print(cSystem.images)
			self.assertTrue(os.path.exists(cSystem.images[url]))
			self.assertTrue(url in cSystem.full_url)
			self.assertTrue(url in cSystem.keywords)
		for url in self.bad_urls:
			print(cSystem.images)
			self.assertFalse(os.path.exists(cSystem.images[url]))
			self.assertFalse(url in cSystem.full_url)
			self.assertFalse(url in cSystem.keywords)
	def testGetFull(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		for url in self.urls:
			cSystem.getFullURL(url)
		self.assertEqual(cSystem.full_url[self.good_quay_url],'https://quay.io/repository/biocontainers/samtools')
		self.assertEqual(cSystem.full_url[self.bad_quay_url],'https://quay.io/repository/biocontainers/samtools')
		self.assertEqual(cSystem.full_url[self.good_dh_url],'https://hub.docker.com/r/biocontainers/samtools')
		self.assertEqual(cSystem.full_url[self.bad_dh_url],'https://hub.docker.com/r/biocontainers/samtools')
	def testGetNameTag(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		cSystem.getNameTag(self.good_dh_url)
		self.assertEqual(cSystem.name_tag[self.good_dh_url], ('samtools', 'v1.7.0_cv2'))
		cSystem.getNameTag('gzynda/singularity')
		self.assertEqual(cSystem.name_tag['gzynda/singularity'], ('singularity', 'latest'))
	def testPullImageForce(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=True)
		for url in self.urls: cSystem.pullImage(url)
		for url in self.good_urls:
			self.assertTrue(os.path.exists(cSystem.images[url]))
		for url in self.bad_urls:
			self.assertFalse(os.path.exists(cSystem.images[url]))
	def testDeleteImage(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=True)
		for url in self.good_urls:
			self.assertFalse(os.path.exists(cSystem.images[url]))
			cSystem.pullImage(url)
			self.assertTrue(os.path.exists(cSystem.images[url]))
			cSystem.deleteImage(url)
			self.assertFalse(os.path.exists(cSystem.images[url]))
	def testMetadata(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		url = self.good_dh_url
		cSystem.getMetadata(url)
		#####################
		self.assertEqual(set(cSystem.keywords[url]), set([]))
		self.assertEqual(set(cSystem.categories[url]), set(['Sequence assembly visualisation', 'Modelling and simulation']))
		self.assertEqual(cSystem.description[url], 'Various utilities for processing alignments in the SAM format, including variant calling and alignment viewing.')
	def testScan(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		for url in self.urls: cSystem.pull(url)
		cSystem.scanAll()
		for url in self.good_urls:
			self.assertTrue(url in cSystem.progs)
		for url in self.bad_urls:
			self.assertFalse(url in cSystem.progs)
	def testCacheProgs(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		with open(self.good_dh_progs,'r') as IF:
			progs = set([l.rstrip('\n') for l in IF.readlines()])
			cSystem.cacheProgs(self.good_dh_url)
			self.assertEqual(cSystem.progs[self.good_dh_url], progs)
	def testFindCommon(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		cSystem.pull(self.good_dh_url)
		cSystem.pull('biocontainers/biocontainers:latest')
		cSystem.scanAll()
		cSystem.findCommon(p=60)
		self.assertTrue('samtools' in cSystem.getProgs(self.good_dh_url))
		self.assertFalse('cp' in cSystem.getProgs(self.good_dh_url))
		self.assertTrue('cp' in cSystem.getProgs(self.good_dh_url, blacklist=False))
	def testGenLMOD(self):
		cSystem = ContainerSystem(cDir=self.cDir, mDir=self.mDir, forceImage=False)
		url = self.good_dh_url
		cSystem.pull(url)
		cSystem.pull('biocontainers/biocontainers:latest')
		cSystem.scanAll()
		cSystem.findCommon(p=60)
		cSystem.genLMOD(url)
		mFile = os.path.join(cSystem.moduleDir, cSystem.name_tag[url][0], cSystem.name_tag[url][1]+'.lua')
		self.assertTrue(os.path.exists(mFile))
		self.assertTrue('samtools' in open(mFile,'r').read())

if __name__ == "__main__":
	unittest.main()
