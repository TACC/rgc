import pytest, logging, os, shutil, tempfile
from collections import Counter
from itertools import product
import subprocess as sp
from time import time

from helpers import del_cache_dir, tmp_file
from rgc.helpers import translate, remove_empty_sub_directories

from rgc.ContainerSystem.scan import scan

urls = ['quay.io/biocontainers/bwa:0.7.3a--hed695b0_5','quay.io/centos/centos:centos7']
shells = ["busybox","bash"]
systems = ['docker', 'singularity3']

programs = {'quay.io/biocontainers/bwa:0.7.3a--hed695b0_5':{'cp', 'traceroute', 'which', 'true', 'ifup', 'mkswap', 'nameif', 'diff', 'pidof', 'mt', 'catv', 'readprofile', 'sleep', 'switch_root', 'ash', 'sha3sum', 'printenv', 'ip', 'gzip', 'ln', 'setlogcons', 'nslookup', 'reset', 'mktemp', 'zcat', 'umount', 'telnet', 'xzcat', 'cpio', 'dnsd', 'route', 'xz', 'chattr', 'udhcpc', 'ipcs', 'unxz', 'date', 'usleep', 'iprule', 'uudecode', 'nohup', 'test', 'chroot', 'rm', 'tail', 'rmdir', 'crond', 'sha512sum', 'nice', 'unzip', 'fdflush', 'cmp', 'makedevs', 'setconsole', 'hdparm', 'fgrep', 'fsck', 'mesg', 'mkfifo', 'resize', 'sync', 'who', 'crontab', 'watchdog', 'bzcat', 'hostid', 'chgrp', 'sulogin', 'ar', 'chvt', 'init', 'uptime', 'grep', 'less', 'lsmod', 'swapoff', 'inetd', 'blkid', 'fuser', 'passwd', 'chown', 'od', 'arping', 'find', 'swapon', 'dumpkmap', 'login', 'pivot_root', 'fdformat', 'yes', 'tr', 'halt', 'runlevel', 'linux32', 'losetup', 'killall5', 'df', 'loadkmap', 'hostname', 'sha1sum', 'kill', 'hwclock', 'mv', 'tee', 'busybox', 'addgroup', 'last', 'patch', 'top', 'lsattr', 'devmem', 'wc', 'sed', 'setkeycodes', 'adduser', 'freeramdisk', 'tftp', 'ls', 'reboot', 'chmod', 'eject', 'xargs', 'logname', 'getty', 'lspci', 'fold', 'mkdir', 'setsid', 'strings', 'setarch', 'mount', 'setserial', 'dd', 'env', 'iproute', 'bunzip2', 'iplink', 'cut', 'iptunnel', 'sh', 'touch', 'lsof', 'gunzip', 'modprobe', 'rdate', 'openvt', 'deallocvt', 'time', 'mknod', 'ifconfig', 'cksum', 'fstrim', 'pipe_progress', 'more', 'uname', 'ps', 'free', 'realpath', 'dirname', 'sort', 'awk', 'klogd', 'vlock', 'install', 'killall', 'dc', 'printf', 'dos2unix', 'linux64', 'lzma', 'syslogd', 'ping', 'mdev', 'bwa', 'hexdump', 'wget', 'ifdown', 'lsusb', 'basename', 'renice', 'netstat', 'id', 'mountpoint', 'chrt', 'expr', 'rmmod', 'ldd', 'bash', 'sha256sum', 'ipcrm', 'pwd', 'unlzma', 'cat', 'lzcat', 'readlink', 'uniq', 'delgroup', 'stty', 'su', 'deluser', 'dmesg', 'ipaddr', 'dnsdomainname', 'microcom', 'tar', 'watch', 'false', 'poweroff', 'uuencode', 'seq', 'unix2dos', 'echo', 'vconfig', 'sysctl', 'loadfont', 'getopt', 'vi', 'clear', 'whoami', 'du', 'head', 'logger', 'egrep', 'tty', 'insmod', 'md5sum'}, \
	'quay.io/centos/centos:centos7':{'find', 'mktemp', 'tload', 'applygnupgdefaults', 'id', 'alternatives', 'factor', 'setcap', 'zgrep', 'namei', 'tar', 'comm', 'halt', 'switch_root', 'nsenter', 'ping6', 'systemctl', 'test', 'chkconfig', 'lsblk', 'colcrt', 'blkdiscard', 'ldconfig', 'sh', 'fsfreeze', 'lz4', 'view', 'zramctl', 'pgrep', 'tty', 'db_dump', 'saslpasswd2', 'pwhistory_helper', 'fmt', 'xargs', 'swapon', 'xzcmp', 'env', 'dnsdomainname', 'uptime', 'xzgrep', 'repodiff', 'hardlink', 'sha384sum', 'column', 'rpmkeys', 'colrm', 'xmlwf', 'chcpu', 'alias', 'read', 'size', 'znew', 'agetty', 'runuser', 'rview', 'addgnupghome', 'depmod', 'tabs', 'unshare', 'umask', 'who', 'udevadm', 'ipcmk', 'nice', 'rvi', 'bootctl', 'umount', 'clock', 'oldfind', 'timedatectl', 'pinentry', 'fdisk', 'sort', 'od', 'i386', 'igawk', 'yumdb', 'pkill', 'utmpdump', 'gpgsplit', 'mkswap', 'sqlite3', 'groupadd', 'db_verify', 'mkhomedir_helper', 'faillock', 'newgidmap', 'init', 'look', 'fg', 'head', 'adduser', 'tracepath6', 'grpconv', 'unalias', 'watchgnupg', 'lsipc', 'zdiff', 'lz4c', 'tracepath', 'certutil', 'getcap', 'du', 'mknod', 'sysctl', 'numfmt', 'lchsh', 'touch', 'elfedit', 'chmod', 'getopts', 'sefcontext_compile', 'lgroupmod', 'gsettings', 'addpart', 'top', 'gencat', 'lscpu', 'telinit', 'write', 'hostid', 'bc', 'whereis', 'flock', 'mkdir', 'objcopy', 'swaplabel', 'chrt', 'findmnt', 'luac', 'signver', 'tsort', 'ln', 'zdump', 'kill', 'gpg', 'diff3', 'ls', 'zcat', 'egrep', 'gpasswd', 'vmstat', 'sha256sum', 'more', 'ionice', 'pwunconv', 'vipw', 'gpgv', 'db_stat', 'link', 'zegrep', 'unxz', 'zforce', 'clear', 'useradd', 'bin', 'uniq', 'logger', 'swapoff', 'pwmake', 'gio', 'pathchk', 'db_replicate', 'pam_tally2', 'lgroupadd', 'ctrlaltdel', 'mkfs', 'chroot', 'chgpasswd', 'xzegrep', 'ifenslave', 'repoclosure', 'sed', 'xzdec', 'info', 'cmsutil', 'dc', 'verifytree', 'ul', 'uname', 'busctl', 'dgawk', 'dwp', 'chardetect', 'scriptreplay', 'ypdomainname', 'pwck', 'lslogins', 'ranlib', 'lz4cat', 'unix_chkpwd', 'xzdiff', 'hwclock', 'tzselect', 'idn', 'cfdisk', 'delpart', 'cksum', 'lslocks', 'db_recover', 'shutdown', 'tic', 'xzcat', 'jobs', 'bashbug', 'userdel', 'ping', 'losetup', 'passwd', 'fdformat', 'unexpand', 'getconf', 'getent', 'newuidmap', 'blkdeactivate', 'cal', 'fsck', 'chsh', 'strings', 'groupmod', 'printf', 'stty', 'false', 'lid', 'modprobe', 'grpck', 'blkid', 'tee', 'gdbus', 'tr', 'infokey', 'db_deadlock', 'sleep', 'ldd', 'sg', 'kpartx', 'iconv', 'setpriv', 'lusermod', 'lsmem', 'dmesg', 'repomanage', 'strip', 'csplit', 'pwd', 'unlink', 'w', 'packer', 'lchfn', 'setarch', 'lchage', 'setsid', 'reset', 'gpgconf', 'lpasswd', 'fallocate', 'arping', 'insmod', 'vigr', 'rm', 'split', 'ldattach', 'stdbuf', 'localedef', 'partx', 'vi', 'crlutil', 'nisdomainname', 'gtar', 'skill', 'grep', 'clockdiff', 'unix_update', 'ipcrm', 'rmmod', 'linux32', 'nohup', 'sfdisk', 'runlevel', 'truncate', 'mkinitrd', 'db_dump185', 'db_hotbackup', 'blockdev', 'chfn', 'db_load', 'db_log_verify', 'pwdx', 'sum', 'df', 'unlz4', 'timeout', 'poweroff', 'getpcaps', 'repoquery', 'pk12util', 'stat', 'tac', 'testgdbm', 'fold', 'rpcgen', 'sha224sum', 'uuidgen', 'sdiff', 'reposync', 'pr', 'lastlog', 'ex', 'db_archive', 'ssltap', 'dir', 'urlgrabber', 'objdump', 'basename', 'rpm', 'lsinitrd', 'tailf', 'hostname', 'col', 'sln', 'sotruss', 'pwconv', 'zmore', 'pmap', 'sprof', 'lnewusers', 'shuf', 'python2', 'ptx', 'newusers', 'join', 'zfgrep', 'install', 'gpgparsemail', 'nl', 'groups', 'whoami', 'wipefs', 'modinfo', 'xz', 'gunzip', 'hexdump', 'sasldblistusers2', 'captoinfo', 'domainname', 'rev', 'sync', 'setfacl', 'echo', 'chpasswd', 'cd', 'db_upgrade', 'wait', 'ipcs', 'lua', 'sbin', 'cpio', 'prlimit', 'expr', 'getopt', 'repotrack', 'rpmverify', 'x86_64', 'yum', 'bg', 'db_checkpoint', 'gzip', 'resizepart', 'xzfgrep', 'slabtop', 'dmfilemapd', 'pgawk', 'lgroupdel', 'newgrp', 'db_tuner', 'reboot', 'cp', 'readprofile', 'journalctl', 'lsns', 'chgrp', 'pydoc', 'rpm2cpio', 'modutil', 'locale', 'mkfifo', 'ar', 'setterm', 'python', 'readlink', 'ps', 'chcon', 'nproc', 'md5sum', 'runcon', 'makedb', 'infotocap', 'yumdownloader', 'realpath', 'dracut', 'gpg2', 'yes', 'renice', 'pam_timestamp_check', 'gawk', 'xmllint', 'loginctl', 'dd', 'kmod', 'rtcwake', 'dmstats', 'tail', 'luserdel', 'gapplication', 'vdir', 'chmem', 'rpmdb', 'cat', 'cut', 'date', 'findfs', 'catchsegv', 'localectl', 'sulogin', 'mcookie', 'dircolors', 'cmp', 'script', 'rename', 'sha512sum', 'dmsetup', 'xmlcatalog', 'linux64', 'nm', 'machinectl', 'nologin', 'expand', 'fc', 'ld', 'raw', 'fstrim', 'luseradd', 'true', 'lsmod', 'fgrep', 'xzmore', 'iconvconfig', 'bash', 'rdisc', 'su', 'dirname', 'seq', 'eject', 'diff', 'toe', 'infocmp', 'wc', 'mkdict', 'gprof', 'login', 'base64', 'capsh', 'readelf', 'geoipupdate', 'hostnamectl', 'coredumpctl', 'xzless', 'addr2line', 'rmdir', 'groupmems', 'getfacl', 'mountpoint', 'pwscore', 'mv', 'db_printlog', 'pldd', 'gzexe', 'tset', 'sha1sum', 'tput', 'chage', 'zic', 'awk', 'pinky', 'users', 'gpgv2', 'rpmquery', 'trust', 'wdctl', 'snice', 'command', 'grpunconv', 'paste', 'chown', 'arch', 'pivot_root', 'zless', 'groupdel', 'free', 'zcmp', 'watch', 'printenv', 'logname', 'usermod', 'isosize', 'curl', 'mount', 'chacl', 'pam_console_apply', 'taskset', 'as', 'shred'}}

def setup_function(function):
	function.cd = tempfile.mkdtemp()
	function.ss = scan()
	function.ss.cache_dir = function.cd
	function.ss.containerDir = tempfile.mkdtemp()

def teardown_function(function):
	del_cache_dir(function.cd)
	del_cache_dir(function.ss.containerDir)
	del function.cd
	del function.ss

@pytest.mark.slow
@pytest.mark.docker
@pytest.mark.singularity
@pytest.mark.parametrize("url,system", product(urls,systems))
def test__ccall(caplog, url, system):
	ss = test__ccall.ss
	ss.system = system
	ss.pull(url)
	assert not ss._ccall(url, 'echo bears')
	assert "Running" in caplog.text

@pytest.mark.slow
@pytest.mark.docker
@pytest.mark.singularity
@pytest.mark.parametrize("url,system", product(urls,systems))
def test__ccheck_output(caplog, url, system):
	ss = test__ccheck_output.ss
	ss.system = system
	ss.pull(url)
	assert ss._ccheck_output(url, 'echo bears') == ["bears"]
	assert "Running" in caplog.text

@pytest.mark.slow
@pytest.mark.docker
@pytest.mark.parametrize("url,shell", zip(urls,shells))
def test__detect_shell(caplog, url, shell):
	ss = test__detect_shell.ss
	ss.system = 'docker'
	ss.pull(url)
	assert shell == ss._detect_shell(url)

@pytest.mark.slow
@pytest.mark.docker
@pytest.mark.singularity
@pytest.mark.parametrize("url,system", product(urls,systems))
def test_scanPrograms(caplog, url, system):
	ss = test_scanPrograms.ss
	ss.system = system
	assert ss.scanPrograms(url)
	assert ss.programs[url] == programs[url]
	assert ss.scanPrograms(url)
	for prog in programs[url]: assert ss.program_count[prog] == 1
	assert ss.scanPrograms(url, force=True)
	for prog in programs[url]: assert ss.program_count[prog] == 2

@pytest.mark.slow
@pytest.mark.docker
def test_scanAll(caplog):
	ss = test_scanAll.ss
	ss.system = 'docker'
	ss.pullAll(urls)
	ss.scanAll()
	for url in urls:
		assert ss.programs[url] == programs[url]
	assert ss.program_count == Counter(programs[urls[0]])+Counter(programs[urls[1]])

@pytest.mark.docker
def test_getPrograms(caplog):
	ss = test_getPrograms.ss
	ss.system = 'docker'
	url = urls[0]
	ss.programs[url] = programs[url]
	assert ss.getPrograms(url, block=True) == list(programs[url])
	ss.block_set = {"ls"}
	assert ss.getPrograms(url, block=True) == list(programs[url] - {"ls"})
	assert ss.getPrograms(url, block=False) == list(programs[url])

@pytest.mark.docker
def test_findCommon(caplog):
	ss = test_findCommon.ss
	ss.system = 'docker'
	for url in urls:
		ss.programs[url] = programs[url]
		ss.program_count += Counter(programs[url])
	ss.findCommon(p=51)
	assert ss.block_set == programs[urls[0]] & programs[urls[1]]
	ss.permit_set = {'ls'}
	ss.findCommon(p=51)
	assert ss.block_set == programs[urls[0]] & programs[urls[1]] - {'ls'}

@pytest.mark.docker
def test_findCommon_baseline(caplog):
	ss = test_findCommon_baseline.ss
	ss.system = 'docker'
	tp = {'bl':{'1','2'},'a':{'1','2','3'},'b':{'3','4'},'c':{'5','6'}}
	for url in tp:
		ss.programs[url] = tp[url]
		ss.program_count += Counter(tp[url])
	ss.findCommon(p=40, baseline=['bl'])
	assert ss.block_set == {'1','2','3'}
