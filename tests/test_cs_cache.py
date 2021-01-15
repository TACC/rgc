import pytest, logging, os, shutil, tempfile

from rgc.ContainerSystem.cache import cache

default_dir = os.path.join(os.path.expanduser('~'),'rgc_cache')
f1 = 'cache1.pkl'

def del_cache_dir(p):
	if os.path.exists(p):
		shutil.rmtree(p)

def test_save_load(caplog):
	#caplog.set_level(logging.DEBUG)
	vals1 = ('a',1)
	c1 = cache()
	c1._cache_save(f1, vals1)
	assert os.path.exists(os.path.join(default_dir, f1))
	assert c1._cache_load(f1, (1,1)) == vals1
	del_cache_dir(default_dir)

def test_save_load_custom_location(caplog):
	vals1 = ('a',1)
	c1 = cache()
	cd = tempfile.mkdtemp()
	c1.cache_dir = cd
	c1._cache_save(f1, vals1)
	assert os.path.exists(os.path.join(cd, f1))
	assert c1._cache_load(f1, (1,1)) == vals1
	del_cache_dir(cd)

def test_save_load_default(caplog):
	del_cache_dir(default_dir)
	assert cache()._cache_load(f1, (1,1)) == (1,1)
	assert not os.path.exists(os.path.join(default_dir))

def test_save_load_force(caplog):
	caplog.set_level(logging.DEBUG)
	vals1 = ('a',1)
	c1 = cache()
	c1._cache_save(f1, vals1)
	c1.force_cache = True
	assert os.path.exists(os.path.join(default_dir, f1))
	assert c1._cache_load(f1, (1,1)) == (1,1)
	assert "Forcing a refresh" in caplog.text
	del_cache_dir(default_dir)
