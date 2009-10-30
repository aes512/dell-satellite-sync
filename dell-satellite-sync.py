#!/usr/bin/env python
#
# _author_ = Vinny Valdez <vvaldez@redhat.com>
# _version_ = 0.2
#
# Copyright (c) 2009 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
# 
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation. 

# Specify Satellite info here if desired, or as parameters (try -h or --help)
SATELLITE_SERVER = ''
SATELLITE_USER = ''
SATELLITE_PASSWORD = ''
LOCAL_REPO = ''

# Dell specific information
# Change this to a specific version as needed
DELL_REPO_URL = 'linux.dell.com/repo/hardware/latest/'	# Defaults to latest, change to remain at a certain version
GPG_URL='http://%s/' % DELL_REPO_URL			# Defaults to public keys
SYSTEM_VENDOR_ID = 'system.ven_0x1028'
PLATFORM_INDEPENDENT = 'platform_independent'		# Subdir of repo that contains platform agnostic rpms
DELL_INFO = { 
		# Careful with the label and name values, they are appended to system ids + base_channel names, and cannot exeed 64 characters
		'label' : 'dell-om',
		'name' : 'Dell OM',
		'summary' : 'Dell OpenManage Software' 
}

# To add a new supported version, add it to the dictionary below.  
SUPPORTED_CHANNELS = {
#		'other_existing_base_channel' : { 'arch' : 'arch_type', 'subdir' : 'subdir within Dell repo' },
		'rhel-i386-as-4' :  { 'arch' : 'i386' , 'subdir' : 'rh40' },
		'rhel-x86_64-as-4' :  { 'arch' : 'x86_64' , 'subdir' : 'rh40_64' },
		'rhel-i386-server-5' :  { 'arch' : 'i386' , 'subdir' : 'rh50' },
		'rhel-x86_64-server-5' :  { 'arch' : 'x86_64' , 'subdir' : 'rh50_64' },

}

# Add channels that share arch and Dell repo subdir to the respective list
RHEL4_i386_ALTS = ['rhel-i386-as-4.5.z','rhel-i386-as-4.6.z','rhel-i386-as-4.7.z','rhel-i386-as-4.8.z','rhel-i386-es-4','rhel-i386-es-4.5.z','rhel-i386-es-4.6.z','rhel-i386-es-4.7.z','rhel-i386-es-4.8.z']
RHEL4_x86_64_ALTS = ['rhel-x86_64-as-4.5.z','rhel-x86_64-as-4.6.z','rhel-x86_64-as-4.7.z','rhel-x86_64-as-4.8.z','rhel-x86_64-es-4','rhel-x86_64-es-4.5.z','rhel-x86_64-es-4.6.z','rhel-x86_64-es-4.7.z','rhel-x86_64-es-4.8.z']
RHEL5_i386_ALTS = ['rhel-i386-server-5.0.z','rhel-i386-server-5.1.z','rhel-i386-server-5.2.z','rhel-i386-server-5.3.ll','rhel-i386-server-5.3.z','rhel-i386-server-5.4.z']
RHEL5_x86_64_ALTS = ['rhel-x86_64-server-5.0.z','rhel-x86_64-server-5.1.z','rhel-x86_64-server-5.2.z','rhel-x86_64-server-5.3.ll','rhel-x86_64-server-5.3.z','rhel-x86_64-server-5.4.z']

###################################################################################
# Clone details on base channels
# RHEL 4 i386 channels
for version in RHEL4_i386_ALTS:
	SUPPORTED_CHANNELS[version] = SUPPORTED_CHANNELS['rhel-i386-as-4']
# RHEL 4 x86_64 channels
for version in RHEL4_x86_64_ALTS:
	SUPPORTED_CHANNELS[version] = SUPPORTED_CHANNELS['rhel-x86_64-as-4']
# RHEL 5 i386 channels
for version in RHEL5_i386_ALTS:
	SUPPORTED_CHANNELS[version] = SUPPORTED_CHANNELS['rhel-i386-server-5']
# RHEL 5 x86_64 channels
for version in RHEL5_x86_64_ALTS:
	SUPPORTED_CHANNELS[version] = SUPPORTED_CHANNELS['rhel-x86_64-server-5']

# Import modules
try:
	import xmlrpclib, os, sys, signal, time, re, getpass, subprocess
	from optparse import OptionParser
except:
	print "Could not import modules"
	raise

# options parsing
usage = "usage: %prog [options]\nThis program will rsync an offline repository from linux.dell.com, then create Satellite channels and populate them with the rpms, and subscribe registered clients to the correct channels.\nUse -h or --help for additional information."
parser = OptionParser(usage=usage, description="")
parser.add_option("-u", "--user", dest="user", help="Satellite username", default=SATELLITE_USER)
parser.add_option("-p", "--password", dest="password", help="Satellite password (will be promoted if omitted)", default=SATELLITE_PASSWORD)
parser.add_option("-s", "--server", dest="satserver", help="FQDN of your Satellite server", default=SATELLITE_SERVER)
parser.add_option("-l", "--localdir", dest="localdir", help="local dir to hold Dell repo", default=LOCAL_REPO)
parser.add_option("-d", "--delete", action="store_true", dest="delete", help="delete existing Dell channels and packages", default=False)
parser.add_option("-f", "--force", action="store_true", dest="force", help="force package upload)", default=False)
parser.add_option("-a", "--all", action="store_true", dest="subscribe_all", help="subscribe all systems, whether Dell vendor or not.", default=False)
parser.add_option("-g", "--gpg-url", dest="gpg_url", help="URL where the GPG keys are located (should be accessible by clients.  e.g. http://satserver.example.com/pub/).", default=GPG_URL)
parser.add_option("--no-rsync", action="store_true", dest="no_rsync", help="skip rsync (local repo must already be present)", default=False)
parser.add_option("--no-packages", action="store_true", dest="no_packages", help="skip uploading packages", default=False)
parser.add_option("-S", "--server-actions-only", action="store_true", dest="server_actions_only", help="only create channels and upload rpms, skip client subscription", default=False)
parser.add_option("-C", "--client-actions-only", action="store_true", dest="client_actions_only", help="only subscribe clients (channels and rpms must already be on server)", default=False)
parser.add_option("-D", "--demo", action="store_true", dest="demo", help="enable demo mode (simulation only, does not connect to a Satellite server)", default=False)
parser.add_option("-v", "--verbose", action="store_true", dest="verbose", help="enable verbose output", default=False)
parser.add_option("--debug", action="store_true", dest="debug", default=False, help="enable lots of debug output (more than verbose)")

(options, terms) = parser.parse_args()

error = False
if options.server_actions_only and options.client_actions_only:
	print "Error: '--server-actions-only' and '--client-actions-only' are mutually exclusive"
	error = True
if options.client_actions_only and options.delete:
	print "Error: currently deleting channels from clients is not supported"
	error = True
if options.user == '':
	print "Error: --user must be specified"
	error = True
if options.satserver == '':
	print "Error: --server must be specified"
	error = True
if (options.localdir == '') and (not options.client_actions_only):
	print "Error: --localdir must specify a dir with write permissions"
	error = True
if error:
	print usage
	sys.exit(1)
else:
	if options.password == '':
		options.password = getpass.getpass()

sat_url = "http://%s/rpc/api" % options.satserver
if options.debug:
	client_verbose = 1
else:
	client_verbose = 0
client = xmlrpclib.Server(sat_url, verbose = client_verbose)

def get_size(dir):
	'''Calls "du -hs" to get directory tree size'''
	du = subprocess.Popen(["du", "-hs", dir], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	du.wait()
	output, errors = du.communicate()
	if options.debug: 
		if not errors == '':
			print errors
	return output.split()[0]
	
def rsync(url, localdir):
	'''Calls rsync, displays spinning line for progress, and updates dir size'''
	# TODO: Enable output for verbose - Currently process hangs, possibly due to too much output
	if options.debug:
		tick = 0
	else:
		tick = 0.5
	progress_bars = [ "|", "/" , "-" , "\\" ]
	num_bars = len(progress_bars) - 1
	try:
		if options.demo:
			size = 0
			print "Simulating rsync process (pid 9999):         ",
			for iters in range(0, 2):
				for bar_char in progress_bars:
					print "\b\b\b\b\b\b\b\b\b\b %4i%s    " % (size, "MB"),
					print "\b\b\b\b\b", progress_bars[progress_bars.index(bar_char)],
					sys.stdout.flush()
					time.sleep(tick)
					size += 50 
		else:
			size = get_size(localdir)
			rsync = subprocess.Popen(["rsync", "-azqH", "rsync://"+url, localdir], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			print "Waiting for rsync process to finish (pid ", rsync.pid,"\b):           ",
			bar_char = 0
			while rsync.poll() is None:
				print "\b\b\b\b\b\b\b\b\b %5s    " % (size),
				print "\b\b\b\b\b", progress_bars[bar_char],
				if bar_char == num_bars:
					bar_char = 0
				else:
					bar_char+=1
				sys.stdout.flush()
				time.sleep(0.5)
				size = get_size(localdir)
		print "\n"
	except KeyboardInterrupt:
		print "Interrupt detected, cleaning up."
		output, errors = rsync.communicate()
		print "stderr on rsync process:", errors
		os.kill(rsync.pid, signal.SIGKILL)
		sys.exit(1)
	if options.demo:
		sys.exit(1)
		return 0
	else:
		output, errors = rsync.communicate()
		if not errors == '':
			print "stderr on rsync process:\n", errors
		return rsync.returncode

def get_dell_repo(repo, localdir):
	'''Calls the rsync function to obtain a local copy of Dell's repos'''
	return rsync(repo, localdir)

def login(user, password):
	'''Login to the Satellite server'''
	return client.auth.login(user, password)

def logout(key):
	'''Logout of the Satellite server'''
	client.auth.logout(key)

def channel_exists(key, channel, channels):
	'''Check if channel exists in the list of channels'''
	if options.demo: return False
	for curchan in channels:
		if channel == curchan['label']:
			if options.debug: print "DEBUG: Match found for %s and %s" % (channel, curchan['label'])
			return True
	if options.debug: print "DEBUG: No match found for", channel
	return False

def create_channel(key, label, name, summary, arch, parent):
	'''Creates a temporary channel, then clones it with GPG key location, then deletes temp channel'''
	if PLATFORM_INDEPENDENT in label:
		channel_map = { 'name' : name, 'label' : label, 'summary' : summary, 'parent_label' : parent, 'gpg_url' : options.gpg_url + 'RPM-GPG-KEY-libsmbios' }
	else:
		channel_map = { 'name' : name, 'label' : label, 'summary' : summary, 'parent_label' : parent, 'gpg_url' : options.gpg_url + 'RPM-GPG-KEY-dell' }
	try:
		if options.verbose: print "Creating temporary channel:", label + '-tmp'
		if options.debug: print "Running: client.channel.software.create(", key, label + '-tmp', name + '-tmp', summary, arch, parent, ")"
		client.channel.software.create(key, label + '-tmp', name + '-tmp', summary, arch, parent)
	except:
		print "Error creating temporary channel:", label + '-tmp'
		raise
	try:
		if options.verbose: print "Cloning temporary channel into real channel:", label
		if options.debug: print "Running: client.channel.software.clone(", key, label + '-tmp', channel_map, True, ")"
		client.channel.software.clone(key, label + '-tmp', channel_map, True)
	except:
		print "Error cloning channel:", label
		raise
	try:
		if options.verbose: print "Deleting temporary channel:", label + '-tmp'
		if options.debug: print "Running: client.channel.software.delete(", key, label + '-tmp', ")"
		client.channel.software.delete(key, label + '-tmp')
	except:
		print "Error deleting channel:", label + '-tmp'
		raise

def delete_channel(key, label):
	'''Deletes a channel on the Satellite server'''
	if options.verbose: print "Deleting channel:", label
	return client.channel.software.delete(key, label)

def build_channel_list(localdir, vendor_id):
	'''Creates a mapping of dirs to their symlink target to use as channel labels/names'''
	dir_list = os.listdir(localdir)
	systems = {}
	for dir in dir_list:
		# Only process directories matching vendor systems
		if vendor_id in dir:
			if os.path.islink(localdir + dir):
				name = os.readlink(localdir + dir)
				if options.debug: print "DEBUG: Using dir link, dir = %s target = %s" % (dir,name)
			else:
				name = dir.split('.')[-1]
				if options.debug: print "DEBUG: Dir is not a link, using part of dir name: %s name = %s" % (dir, name)
			systems[dir] = name
	if options.debug: print "DEBUG: Systems mapping:", systems
	return systems

def gen_rpm_list(path):
	'''Walk dir tree in path and return a list of rpms found'''
	rpms = []
	if os.path.isdir(path):		# Dir should exist, but just to be safe
		os.chdir(path)
		for root, dirs, files in os.walk("."):
			for name in files:
				if re.search('\.rpm$', name):
					rpms.append(os.path.join(root,name))
					if options.debug: print "DEBUG: + adding rpm:", name
				else:
					if options.debug: print "DEBUG: - not an rpm:", name
	if options.debug: print "DEBUG: returning list of rpms:", rpms
	return rpms

def push_rpm(rpm, channel, user, password, satserver):
	'''Push rpm into Satellite using rhnpush as needed'''
	if options.debug:
		verbose_flag = '-vv'
	elif options.verbose:
		verbose_flag = '-v'
	else:
		verbose_flag = ''
	if re.search('\.src\.rpm$', rpm):
		# source rpm, setting --source flag
		source_flag = '--source'
	else:
		source_flag = ''
	if options.force:
		force_flag = '--force'
	else:
		force_flag = ''
	# call rhnpush subprocess
	try:
		if options.verbose: print "Calling rhnpush to upload %s into %s:" % (rpm.split('/')[-1], channel)
		if not options.demo:
			rhnpush = subprocess.Popen(['rhnpush', source_flag, '--channel', channel, '--username', options.user, '--password', password, '--server', 'http://' + satserver + '/APP', rpm, verbose_flag, force_flag ], shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
			rhnpush.wait()
	except KeyboardInterrupt:
		print "Interrupt detected, cleaning up."
		output, errors = rhnpush.communicate()
		print "stderr on rhnpush process:", errors
		os.kill(rhnpush.pid, signal.SIGKILL)
		sys.exit(1)
	if options.demo: 
		return 0
	else:
		output, errors = rhnpush.communicate()
		if (options.verbose) or (not rhnpush.returncode == 0): 
			print output
			if not errors == '':
				print "stderr on rhnpush process:\n", errors
			print "rhnpush exited with returncode:", rhnpush.returncode
		return rhnpush.returncode

def subscribe(key, base_channel, new_channel, system_id, system_name):
	'''Subscribes system_id to new_channel'''
	# Get a list of current child channels, since subscribe removes all channels
	channels = client.system.list_subscribed_child_channels(key, system_id)
	channel_labels = []
	for channel in channels:
		channel_labels.append(channel['label'])
	if new_channel in channel_labels:
		if options.verbose: print "%s is already subscribed to %s." % (system_name, new_channel)
		return True
	available_channels = client.system.list_subscribable_child_channels(key, system_id)
	available_channel_labels = []
	for channel in available_channels:
		available_channel_labels.append(channel['label'])
	if new_channel not in available_channel_labels:
		if options.verbose: print "Attemped to subscribe %s to %s, but it is not available." % (system_name, new_channel)
		return False
	if options.verbose: print "Subscribing %s to %s" % (system_name, new_channel)
	channel_labels.append(new_channel)
	return client.system.set_child_channels(key, system_id, channel_labels)

def subscribe_clients(key):
	'''Creates list of registered clients, and subscribes them to the platform_independent channel'''
	systems = client.system.list_systems(key)
	scheduled = []
	for system in systems:
		# Check if it is a Dell system
		if options.verbose: print "Checking system %s with id: %i" % (system['name'], system['id'])
		system_dmi = client.system.get_dmi(key, system['id'])
		if system_dmi == '':
			vendor = 'unknown'
		else:
			vendor = system_dmi['vendor']
		if not ('Dell' in vendor or options.subscribe_all):
			print "%s vendor is '%s', skipping.  Force with --all if desired." % (system['name'], vendor)
			if options.verbose: print "Removing %s from list" % (system['name'])
			system['skip'] = True
		else:
			if options.verbose: print "%s vendor is: '%s'" % (system['name'], vendor)
			system['skip'] = False
			try:
				base_channel = client.system.get_subscribed_base_channel(key, system['id'])['label']
				system['base_channel'] = base_channel
				if options.verbose: print "%s is subscribed to base channel: %s." % (system['name'], base_channel)
				scheduled.append(system['id'])
				new_channel = DELL_INFO['label'] + '-' + PLATFORM_INDEPENDENT + '-' + base_channel
				system['platform_independent'] = new_channel
				if not subscribe(key, base_channel, new_channel, system['id'], system['name']):
					system['skip'] = True
					if options.verbose: print "Error attempting to subscribe %s to %s." % (system['name'], new_channel)
#					sys.exit(1)
			except:
				print "No base channel found for %s.  Please subscribe this system to a supported channel first." % (system['name'])
				raise
	return systems

def schedule_actions(key, systems):
	'''Schedules GPG key install, package install, and "smbios-sys-info" action on clients'''
	gpg_script = '''
#!/bin/bash
# Check if libsmbios gpg key is installed
rpm -q gpg-pubkey-5e3d7775-42d297af
if [ ! "$?" = "0" ]
then
	echo Importing RPM-GPG-KEY-libsmbios
	rpm --import ''' + options.gpg_url + 'RPM-GPG-KEY-libsmbios' + '''
fi
# Check if dell gpg key is installed
rpm -q gpg-pubkey-23b66a9d-3adb5504
if [ ! "$?" = "0" ]
then
	echo Importing RPM-GPG-KEY-dell
	rpm --import ''' + options.gpg_url + 'RPM-GPG-KEY-dell' + '''
fi
	'''
	action_script = '''
#!/bin/bash
rpm -q smbios-utils
if [ ! "$?" = "0" ]
then
	echo Waiting for smbios-utils to be installed
	sleep 60
fi
/usr/sbin/smbios-sys-info
	'''
	for system in systems:
		if system['skip']: continue
		# First find the package id for smbios-utils
		smbios_packages = client.packages.search.advanced_with_channel(key, "name:smbios-utils AND description:meta-package", system['platform_independent'])
		smbios_packages.sort()
		if options.debug: print "DEBUG: %s package search results:" % (system['name'], smbios_packages)
		smbios_package = smbios_packages[-1]['id']
		# First try to schedule gpg key imports for libsmbios and dell
		try:
			client.system.schedule_script_run(key, system['id'], "root", "root", 14400, gpg_script, system['last_checkin'])
		except:
			print "Error trying to schedule gpg key install for %s" % system['name']
			system['skip'] = True
			if options.debug: raise
			continue 
		# Now schedule package install for smbios-utils
		try:
			# Find smbios-utils in newly subscribed channel, and schedule install
			if options.verbose: print "Scheduling package install '%s' (%i) on %s" % ('smbios-utils', smbios_package, system['name']) 
			# TODO: Need to schedule it 1 minute after 'last_checkin' to avoid race condition with gpg keys
			result = client.system.schedule_package_install(key, system['id'], smbios_package, system['last_checkin'])
			if options.verbose: print "Result of package scheduling for %s: %i" % (system['name'], result)
		except:
			print "Error trying to install 'smbios-utils' package for %s" % system['name']
			system['skip'] = True
			if options.debug: raise
			continue
		if options.verbose: print "Scheduling action on system: %s id: %i" % (system['name'], system['id'])
		# TODO: schedule this 2 minutes after 'last_checkin'
		system['action_id'] = client.system.schedule_script_run(key, system['id'], "root", "root", 14400, action_script, system['last_checkin'])
		system['complete'] = False
	return systems

def get_action_results(key, systems):
	'''Gets action results that have been scheduled'''
	if options.debug:
		wait = 5
	elif options.verbose:
		wait = 15
	else:
		wait = 30
	complete = False

	while not complete:
		for system in systems:
			if system['skip']: continue
			if not system['complete']:
				if options.verbose: print "checking system:", system['name']
				script_result = client.system.get_script_results(key, system['action_id'])
				if (options.verbose) and (not script_result == []): 
					print "Script result for %s: %s:" % (system['name'], script_result)
				if not script_result == []:
					if options.verbose: print "%s script result:" % (system['name'])
					if options.debug: print script_result
					system['output'] = script_result[0]['output']
					system['return_code'] = script_result[0]['returnCode']
					system['complete'] = True
				else:
					system['complete'] = False
					if options.verbose: print "%s not completed yet." % (system['name'])
		complete = True
		for system in systems:
			if system['skip']: continue
			if not system['complete']:
				complete = False
		if not complete:
			print "waiting %i seconds for results ..." % (wait)
			time.sleep(wait)

	for system in systems:
		if system['skip']: continue
		data = system['output'].split('\n')
		if options.debug: print "DEBUG: Raw output from %s script: %s" %(system['name'], data)
		for line in data:
			if options.debug: print "DEBUG: %s checking '%s'" % (system['name'], line)
			if 'System ID:' in line:
				if options.verbose: print "Found system_id of:", line.split()[-1]
				system['system_id'] = line.split()[-1].lower()
				break
		else:
			system['system_id'] = False
	for system in systems:
		if system['skip']: continue
		if options.verbose: print "System ID for %s is: %s" % (system['name'], system['system_id'])
		new_channel = DELL_INFO['label'] + '-' + SYSTEM_VENDOR_ID + '.dev_' + system['system_id'] + '-' + system['base_channel']
		system['system_channel'] = new_channel
		if options.verbose: print "Subscribing %s to channel %s" % (system['name'], system['system_channel'])
		if not subscribe(key, system['base_channel'], system['system_channel'], system['id'], system['name']):
			system['no_child'] = True
		else:
			system['no_child'] = False
	return systems

def show_client_results(systems):
	skipped = []
	completed = []
	no_child = []
	for system in systems:
		if system['skip']: 
			skipped.append(system['name'])
		elif system['no_child']:
			no_child.append(system['name'])
		elif system['complete']:
			completed.append(system['name'])
	if completed == []:
		print "No systems were successfully completed."
	else:
		print "The following systems were completed: %s" % completed
	if not skipped == []:
		print "The following systems were skipped: %s" % skipped
	if not no_child == []:
		print "The following do not have system-specific child channels: %s" % no_child

def reconstruct_name(package):
	'''Take dictionary of package name in Satellite and reconstruct the full name'''
	# Map: name, version, release, epoch, arch_label
	if package['epoch'] == '':
		full_name = '-'.join([package['name'], package['version'], package['release']])
	else:
		full_name = '-'.join([package['name'], package['version'], package['release'] + ':' + package['epoch']])
	return full_name + '.' + package['arch_label']

def main():
	if options.demo: 
		key = False
		current_channels = {}
		current_channel_labels = ['rhel-x86_64-server-5']
	else:
		# Login to Satellite server
		key = login(options.user, options.password)
		# Build existing channel list
		current_channels = client.channel.list_all_channels(key)
		current_channel_labels = []
		for channel in current_channels:
			current_channel_labels.append(channel['label'])
		if options.debug: print "DEBUG: Channels on current Satellite server:", current_channel_labels
		if client.api.get_version() < 5.1:
			# TODO: Haven't tested with Spacewalk, not sure how it is reported
			print "This script uses features not available with Satellite versions older than 5.1"
			sys.exit(1)
	if not options.client_actions_only:
		# This begins the server actions section
		if not os.path.exists(options.localdir):
			try:
				os.makedirs(options.localdir)
			except:
				print "Error: Unable to create %s" % (options.localdir)
				raise
		if (not options.delete) and (not options.no_rsync):
			# Sync local Dell repo with public Dell repo
			returncode = get_dell_repo(DELL_REPO_URL, options.localdir)
			if not returncode == 0:
				print "rsync process exited with returncode:", returncode
		# Build child channels based on dell repo as needed
		systems = build_channel_list(options.localdir, SYSTEM_VENDOR_ID)
		systems['platform_independent'] = PLATFORM_INDEPENDENT
		# Iterate through list of supported RHEL versions and archs, create parent channels if needed
		channels = {}
		print "Checking base channels on Satellite server"
		for parent in SUPPORTED_CHANNELS:
			if options.verbose: print "Checking base channel", parent
			# Check each supported base channel, skip if it does not exist on Satellite server
			if parent not in current_channel_labels:
				if options.verbose: print "-%s is not a current base channel, skipping." % (parent)
				continue
			else:
				channels[parent] = SUPPORTED_CHANNELS[parent]
				channels[parent]['child_channels'] = []		# Initialize key for child channels
				if options.verbose: print "+%s found on Satellite server, checking child channels." % (parent)
			if channels[parent]['arch'] == 'i386':
				# This is because Satellite stores x86 as 'ia32'
				arch = 'channel-ia32'
			else:
				arch = 'channel-' + channels[parent]['arch']
			subdir = channels[parent]['subdir']
			
			print "  Checking child channels for %s" % parent
			for system in systems:
				# use system name plus parent to create a unique child channel
				c_label = DELL_INFO['label'] + '-' + system + '-' + parent
				c_name = DELL_INFO['name'] + ' on ' + systems[system] + ' for ' + parent
				c_summary = DELL_INFO['summary'] + ' on ' + systems[system] + ' running ' + parent
				c_arch = arch
				c_dir = options.localdir + system + '/' + subdir
				if options.verbose: print "    Checking child channel:", c_label
				if channel_exists(key, c_label, current_channels):
					if options.delete:
						# Delete child channels if requested
						if options.demo:
							print "Deleting channel:", c_label
						else:
							delete_channel(key, c_label)
					else:
						if options.debug: print "DEBUG: checking for dir:", c_dir
						if options.verbose: print "Child channel already exists:", c_label
						if os.path.isdir(c_dir):
							channels[parent]['child_channels'].append(system)
				else:
					if not options.delete:
						# Build child channels if needed
						if options.debug: print "DEBUG: checking for dir:", c_dir
						if os.path.isdir(c_dir):
							channels[parent]['child_channels'].append(system)
							if options.debug: print "DEBUG: %s exists for %s, creating channel" % (subdir, system)
							if options.demo:
								if options.verbose: print "Creating child channel:", c_label
							else:
								create_channel(key, c_label, c_name, c_summary, c_arch, parent)
						else:
							if options.debug: print "DEBUG: %s does not exists for %s" % (subdir, system)

		if (not options.delete) and (not options.no_packages):
			# Iterate through channels, pushing rpms from the local repo as needed
			# TODO: check if rpm is already uploaded and orphaned or part of another channel
			if options.debug: print "DEBUG: Channel mapping:", channels
			print "Syncing rpms as needed"
			for parent in channels:
				print "  Syncing rpms for child channels in %s" % parent
				for child in channels[parent]['child_channels']:
					dir = options.localdir + child + '/' + channels[parent]['subdir']
					channel = DELL_INFO['label'] + '-' + child + '-' + parent
					if options.verbose: print "    Syncing rpms to child channel", channel
					if options.debug: print "DEBUG: Looking for rpms in", dir
					rpms = gen_rpm_list(dir)
					# Get all packages in child channel
					existing_packages = client.channel.software.list_all_packages(key, channel)
					if options.debug: print "DEBUG: Existing packages in", channel, existing_packages
					for rpm in rpms:
						if options.debug: print "DEBUG: Working on:", rpm
						# Strip off '.rpm' at end of file to match against existing entries
						rpm_name = rpm.split('.rpm')[0]
						# Now strip off any preceeding paths
						rpm_name = rpm_name.split('/')[-1]
						# Iterate through existing packages, and skip existing ones
						if options.verbose: print "Checking if %s is already on the Satellite server in %s" % (rpm_name, channel)
						for package in existing_packages:
							existing_rpm_name = reconstruct_name(package)
							if options.debug: print "DEBUG: Checking match for %s and %s" % (rpm_name, existing_rpm_name)
							if existing_rpm_name == rpm_name:
								# This means the intended rpm is already in Satellite, so skip
								if options.verbose: print "- %s already in Satellite, skipping" % (rpm_name)
								break
						else:
							if options.verbose: print "+ %s is not in Satellite, adding" % (rpm_name)
							if options.debug: print "DEBUG: Calling: push_rpm(",rpm, channel, options.user, options.password, options.satserver, ")"
							returncode = push_rpm(rpm, channel, options.user, options.password, options.satserver)
							if not returncode == 0:
								print "rhnpush process exited with returncode:", returncode
								if returncode == 255:
									print "You may force package uploads with --force"
								sys.exit(1)
			print "Completed uploading rpms."

	if (not options.server_actions_only) and (not options.demo) and (not options.delete):
		# This is the client actions section
		print "Subscribing registered systems to the %s channel" % (PLATFORM_INDEPENDENT)
		client_systems = subscribe_clients(key)
		print "Scheduling software installation and actions on clients"
		client_systems = schedule_actions(key, client_systems)
		print "Waiting for client actions to complete"
		client_systems = get_action_results(key, client_systems)
		print "All actions completed.\n"
		show_client_results(client_systems)

	if not options.demo: logout(key)

if __name__ == "__main__":
	main()
