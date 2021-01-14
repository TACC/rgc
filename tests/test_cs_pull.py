import pytest, logging, os, shutil, tempfile
from itertools import product
import subprocess as sp
from time import time

from helpers import del_cache_dir, tmp_file
from rgc.ContainerSystem.pull import pull
from rgc.helpers import translate, remove_empty_sub_directories

default_dir = os.path.join(os.path.expanduser('~'),'rgc_cache')
restorable_cache = os.path.join(os.path.dirname(__file__), 'scache.tar')

def setup_function(function):
	function.cd = tempfile.mkdtemp()
	function.ps = pull()
	function.ps.cache_dir = function.cd
	function.ps.containerDir = tempfile.mkdtemp()

def teardown_function(function):
	del_cache_dir(function.cd)
	del_cache_dir(function.ps.containerDir)
	del function.cd
	del function.ps

@pytest.mark.singularity
@pytest.mark.slow
def test_sing_cache(caplog):
	ps = test_sing_cache.ps
	ps.system = 'singularity3'
	ps.cache_docker_images = ['quay.io/biocontainers/bwa:0.7.17--hed695b0_7','quay.io/biocontainers/bwa:0.7.3a--hed695b0_5']
	assert not ps.layer_cache
	ps._makeSingularityCache()
	assert "tar" in ps.layer_cache
	assert os.path.exists(ps.layer_cache)
	#print(os.stat(ps.layer_cache).st_size)
	assert not os.path.exists(os.path.join(ps.cache_dir,'scache'))
	assert "Creating the base layer cache." in caplog.text

@pytest.mark.dockerhub
@pytest.mark.singularity
@pytest.mark.slow
def test_sing_cache_speed(caplog):
	ps = test_sing_cache_speed.ps
	ps.system = 'singularity3'
	# Add URL and check metadata
	url = 'biocontainers/bwa:v0.7.17_cv1'
	ps.parseURL(url)
	assert ps.singularity_url[url] == 'docker://%s'%(url)
	# Output image
	img_out, img_dir, simg = tmp_file(split=True)
	# Run and time pull without cache
	time_start_no_cache = time()
	ps._pullSingularity(url, img_dir, simg)
	time_no_cache = time()-time_start_no_cache
	assert "Extracting" not in caplog.text
	assert os.path.exists(img_out)
	os.remove(img_out)
	caplog.clear()
	# Run and time pull with cache
	if os.path.exists(restorable_cache):
		os.symlink(restorable_cache, os.path.join(ps.cache_dir, 'scache.tar'))
		ps._makeSingularityCache()
		assert "Using found layer" in caplog.text
	else:
		ps._makeSingularityCache()
		shutil.copyfile(ps.layer_cache, restorable_cache)
	time_start_cache = time()
	ps._pullSingularity(url, img_dir, simg)
	time_cache = time()-time_start_cache
	assert "Extracting" in caplog.text
	assert os.path.exists(img_out)
	os.remove(img_out)
	print("No cache: %.1f seconds\nWith Cache: %.1f seconds"%(time_no_cache, time_cache))
	assert time_cache < time_no_cache

@pytest.mark.singularity
@pytest.mark.slow
def test__pullSingularity(caplog):
	ps = test__pullSingularity.ps
	ps.system = 'singularity3'
	url = 'quay.io/biocontainers/bwa:0.7.3a--hed695b0_5'
	img_out, img_dir, simg = tmp_file(split=True)
	ps.parseURL(url)
	ret = ps._pullSingularity(url, img_dir, simg, cache_dir=False, clean=True, keep_img=True)
	assert os.path.exists(img_out)
	assert ret == img_out
	os.remove(img_out)
	ret = ps._pullSingularity(url, img_dir, simg, cache_dir=False, clean=True, keep_img=False)
	assert not os.path.exists(img_out)

@pytest.mark.docker
@pytest.mark.slow
def test__pullDocker(caplog):
	ps = test__pullDocker.ps
	ps.system = 'docker'
	url = 'quay.io/biocontainers/bwa:0.7.3a--hed695b0_5'
	sp.call("docker rmi %s &> /dev/null"%(url), shell=True)
	img_out, img_dir, simg = tmp_file(split=True)
	ps.parseURL(url)
	ret = ps._pullDocker(url, img_dir, simg)
	assert '0.7.3a--hed695b0_5' in translate(sp.check_output('docker images | grep "quay.io/biocontainers/bwa"', shell=True)).rstrip('\n')
	assert ret == url
	assert not os.path.exists(img_out)
	sp.call("docker rmi %s &> /dev/null"%(url), shell=True)

@pytest.mark.docker
@pytest.mark.slow
def test__pullImage_docker(caplog):
	ps = test__pullImage_docker.ps
	ps.system = 'docker'
	url = 'quay.io/biocontainers/bwa:0.7.3a--hed695b0_5'
	sp.call("docker rmi %s &> /dev/null"%(url), shell=True)
	ps.parseURL(url)
	ret = ps._pullImage(url)
	assert '0.7.3a--hed695b0_5' in translate(sp.check_output('docker images | grep "quay.io/biocontainers/bwa"', shell=True)).rstrip('\n')
	assert ps.images[url] == url
	assert not os.path.exists(os.path.join(ps.containerDir, 'bwa'))
	sp.call("docker rmi %s &> /dev/null"%(url), shell=True)

@pytest.mark.singularity
@pytest.mark.slow
def test__pullImage_singularity(caplog):
	ps = test__pullImage_singularity.ps
	ps.system = 'singularity3'
	url = 'quay.io/biocontainers/bwa:0.7.3a--hed695b0_5'
	sp.call("docker rmi -f %s &> /dev/null"%(url), shell=True)
	ps.parseURL(url)
	ret = ps._pullImage(url)
	assert ret == True
	assert ps.system == 'singularity3'
	assert '0.7.3a--hed695b0_5' not in translate(sp.check_output('docker images', shell=True)).rstrip('\n')
	assert ps.images[url] == os.path.join(ps.containerDir, 'bwa', 'bwa-0.7.3a--hed695b0_5.sif')
	assert os.path.exists(ps.images[url])

urls = ['quay.io/biocontainers/bwa:0.7.3a--hed695b0_5','quay.io/biocontainers/bears:latest']
systems = ['docker','singularity3']

@pytest.mark.singularity
@pytest.mark.docker
@pytest.mark.slow
@pytest.mark.parametrize("url,system", product(urls, systems))
def test_pull(caplog, url, system):
	ps = test_pull.ps
	ps.system = system
	sp.call("docker rmi -f %s &> /dev/null"%(url), shell=True)
	ret = ps.pull(url)
	if 'latest' not in url:
		assert ret
		assert url in ps.valid and url not in ps.invalid
		assert ps.categories[url] == ['Read mapping']
		assert ps.keywords[url] == ['Mapping']
		assert ps.description[url] == "Fast, accurate, memory-efficient aligner for short and long sequencing reads"
		assert ps.homepage[url] == 'http://bio-bwa.sourceforge.net'
		if ps.system == 'docker':
			assert '0.7.3a--hed695b0_5' in translate(sp.check_output('docker images | grep "quay.io/biocontainers/bwa"', shell=True))
			assert ps.images[url] == url
			assert not os.path.exists(os.path.join(ps.containerDir, 'bwa'))
		else:
			assert '0.7.3a--hed695b0_5' not in translate(sp.check_output('docker images', shell=True)).rstrip('\n')
			assert ps.images[url] == os.path.join(ps.containerDir, 'bwa', 'bwa-0.7.3a--hed695b0_5.sif')
			assert os.path.exists(ps.images[url])
	else:
		assert not ret
		assert url not in ps.valid and url in ps.invalid
		assert "Not pulling" in caplog.text
		assert url not in ps.categories
		assert url not in ps.keywords
		assert url not in ps.homepage
		assert url not in ps.description

@pytest.mark.singularity
@pytest.mark.slow
def test_pullAll(caplog):
	ps = test_pullAll.ps
	ps.system = 'singularity3'
	urls = ['quay.io/biocontainers/bwa:0.7.3a--hed695b0_5','quay.io/biocontainers/bears:latest']
	# Run and time pull with cache
	if os.path.exists(restorable_cache):
		os.symlink(restorable_cache, os.path.join(ps.cache_dir, 'scache.tar'))
		ps._makeSingularityCache()
		assert "Using found layer" in caplog.text
	ps.pullAll(urls)
	assert ps.images[urls[0]] == os.path.join(ps.containerDir, 'bwa', 'bwa-0.7.3a--hed695b0_5.sif')
	assert os.path.exists(ps.images[urls[0]])
	assert not os.path.exists(os.path.join(ps.containerDir, 'bears'))

def test_sing_cache_exists(caplog):
	ps = test_sing_cache_exists.ps
	cache_file = os.path.join(ps.cache_dir, 'scache.tar')
	assert not os.path.exists(cache_file)
	open(cache_file,'w').close()
	ps._makeSingularityCache()
	assert "Using found layer cache" in caplog.text
	caplog.clear()
	ps._makeSingularityCache()
	assert "Using existing layer cache" in caplog.text

def test__pullWarn(caplog):
	ps = test__pullWarn.ps
	ps._pullWarn("cats")
	assert "You have reached your pull limit on Docker Hub." not in caplog.text
	assert not ps.reached_pull_limit
	caplog.clear()
	ps._pullWarn("You have reached your pull rate limit")
	assert "You have reached your pull limit on Docker Hub." in caplog.text
	assert ps.reached_pull_limit
	caplog.clear()
	ps._pullWarn("You have reached your pull rate limit")
	assert "You have reached your pull limit on Docker Hub." not in caplog.text

def test_remove_empty_sub_directories():
	ps = test_remove_empty_sub_directories.ps
	cd = test_remove_empty_sub_directories.cd
	assert os.path.exists(cd)
	for d in 'abcd':
		os.makedirs(os.path.join(cd, d))
		if not d == 'd': open(os.path.join(cd, d, 'v'), 'w').close()
	remove_empty_sub_directories(cd)
	known_list = sorted((os.path.join(cd,d,'v') for d in 'abc'))
	found_list = sorted((os.path.join(p,f) for p,dl,fl in os.walk(cd) for f in fl))
	assert known_list == found_list
	remove_empty_sub_directories(cd)
	found_list = sorted((os.path.join(p,f) for p,dl,fl in os.walk(cd) for f in fl))
	assert known_list == found_list
