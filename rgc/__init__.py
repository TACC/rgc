#!/usr/bin/env python
#
###############################################################################
# Author: Greg Zynda
# Last Modified: 06/22/2020
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

import sys, argparse, os, json, logging
logger = logging.getLogger(__name__)

from .version import version as __version__
from rgc.ContainerSystem import ContainerSystem

# Environment
FORMAT = '[%(levelname)s - %(name)s.%(funcName)s] %(message)s'

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
	parser.add_argument('-T', '--tracker', metavar='STR', \
		help='Google form tracker URL', default='', type=str)
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
		logger.debug("DEBUG logging enabled")
	else:
		logging.basicConfig(level=logging.INFO, format=FORMAT)
	################################
	# Create container system
	################################
	cSystem = ContainerSystem(module_dir=args.moddir, \
			container_dir=args.imgdir, cache_dir=args.cachedir, \
			module_system='lmod', force=False, \
			force_cache=args.force, n_threads=args.threads)
	logger.info("Finished initializing system")
	################################
	# Define default URLs
	################################
	defaultURLS = ['centos:7', 'continuumio/miniconda:latest', \
		'biocontainers/biocontainers:vdebian-buster-backports_cv1', \
		'gzynda/build-essential:bionic']
	logger.debug("Using the following images as baselines: %s"%(str(defaultURLS)))
	################################
	# Validate all URLs
	################################
	cSystem.validateURLs(defaultURLS+args.urls, args.include_libs)
	logger.debug("DONE validating URLs")
	################################
	# Pull all URLs
	################################
	cSystem.pullAll(defaultURLS+args.urls, delete_old=args.delete_old, use_cache=True)
	logger.debug("DONE pulling all urls")
	################################
	# Process all images
	################################
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
	cSystem.genModFiles(pathPrefix=args.prefix, contact_url=args.contact, \
		mod_prefix=args.modprefix, delete_old=args.delete_old, \
		tracker_url=args.tracker, force=False, lmod_prereqs=requires.split(','))
	logger.debug("DONE creating Lmod files for all %i containers"%(len(args.urls)))

if __name__ == "__main__":
	main()
