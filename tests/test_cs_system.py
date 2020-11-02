import pytest, logging
from helpers import mock
from itertools import product

import rgc.ContainerSystem.system as rsys

singularity_responses = (b"2.6.0-dist",b"singularity version 3.3.0-1.fc29",b"singularity version 4.1")
singularity_versions = ('singularity2','singularity3','singularity4')

@pytest.mark.parametrize("response,final", zip(singularity_responses,singularity_versions))
def test__detectSingularity(caplog, response, final):
	#singularity version 3.3.0-1.fc29
	#2.6.0-dist
	m = mock({'singularity --version':response})
	caplog.set_level(logging.DEBUG)
	rsys.sp.call = m.false
	rsys.sp.check_output = m.false
	s = rsys.system()
	assert s._detectSingularity() == final

@pytest.mark.parametrize("which_response,info_response", product((False,True), repeat=2))
def test__detectDocker(caplog, which_response, info_response):
	m = mock({'which docker &>/dev/null':which_response, 'docker info &>/dev/null':info_response})
	caplog.set_level(logging.DEBUG)
	rsys.sp.call = m.true
	detected = rsys.system()._detectDocker()
	if which_response:
		assert detected == False
	else:
		assert "Detected docker on the system PATH" in caplog.text
		if info_response:
			assert "Does docker need to be activated or run with sudo?" in caplog.text
			assert detected == False
		else:
			assert detected == 'docker'

@pytest.mark.parametrize("which_response,info_response,help_response,s_tup,target", \
	product(*[[0,1]]*3, zip(singularity_responses, singularity_versions), ('docker','singularity','bears',False)))
def test__detectSystem(caplog, which_response, info_response, help_response, s_tup, target):
	sing_r, sing_v = s_tup
	mock_call = mock({'which docker &>/dev/null':which_response, \
		'docker info &>/dev/null':info_response, \
		'singularity help &>/dev/null':help_response})
	mock_check_output = mock({'singularity --version':sing_r})
	rsys.sp.call = mock_call.true
	rsys.sp.check_output = mock_check_output.false
	caplog.set_level(logging.DEBUG)
	# Check raise
	if target not in ('docker','singularity',False):
		with pytest.raises(ValueError):
			rsys.system()._detectSystem(target=target)
	elif not target:
		if which_response or info_response:
			if help_response:
				with pytest.raises(SystemError):
					rsys.system()._detectSystem()
				with pytest.raises(SystemError):
					rsys.system()._detectSystem(target=target)
			else:
				assert rsys.system()._detectSystem() == sing_v
				assert rsys.system()._detectSystem(target=target) == sing_v
		else:
			assert rsys.system()._detectSystem() == 'docker'
			assert rsys.system()._detectSystem(target=target) == 'docker'
	elif target == 'singularity':
		if help_response:
			with pytest.raises(ValueError):
				rsys.system()._detectSystem(target=target)
		else:
			assert rsys.system()._detectSystem(target=target) == sing_v
	elif target == 'docker':
		if which_response or info_response:
			with pytest.raises(ValueError):
				rsys.system()._detectSystem(target=target)
		else:
			assert rsys.system()._detectSystem(target=target) == 'docker'
