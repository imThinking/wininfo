__title__ = 'wininfo'
__version__ = '0.1'
__author__ = 'ZHOU'
__license__ = 'Apache v2.0 License'


# Get Local Windows System information by WMI.
import csv
import subprocess
from optparse import OptionParser
from sys import exit
import tkinter 
from PIL import ImageGrab

from win32 import win32api, win32gui, win32print
from win32.lib import win32con
from win32.win32api import GetSystemMetrics
# convert a command line argument string, with 2 variables, eg arg1-arg2 into a list eg [arg1, arg2]
# especially for IP addresses range
def doublearg2list(doublearg):
	arglist = doublearg.split('-')
	return arglist

# execute a Windows command with subprocess, 'command'
def run_cmd(command):
	p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE)
	stdout, stderr = p.communicate()
	if p.returncode!=0:
		print 'DOS command failed'

# make list if WMIC queries
wmicswitch = list()
wmicswitch.append(['computersystem', 'name'])
wmicswitch.append(['computersystem', 'manufacturer'])
wmicswitch.append(['computersystem', 'model'])
wmicswitch.append(['bios', 'serialnumber'])
wmicswitch.append(['os', 'caption'])
wmicswitch.append(['os', 'installdate'])
wmicswitch.append(['nicconfig', 'ipaddress'])
# header for output file
header = ['Hostname', 'Manufacturer', 'Model', 'Service tag', 'Operating system', 'Install date', 'IP address']
# if additional query provided as command line argument, add to list
if options.wmicquery is not None:
	query = doublearg2list(options.wmicquery)
	wmicswitch.append(query)
	header.append(query[1])

##########################################################################
# run WMIC queries and export results to csv
##########################################################################	
# initialize empty list for all hosts data to be appended
computerdata = list()

# loop through hosts and get wmic info
for i, host in enumerate(hosts):
	print 'Querying '+host
	# initialize empty list for a single hosts data
	compspec = list()
	# loop through wmic commands
	for switch in wmicswitch:
		wmicfile='wmicresponse.txt'
		# execute wmic command saving output to wmicfile
		wmiccommand='wmic' + ' /user:%s' % options.user + ' /password:%s' % options.password + ' /node:%s' % host + ' %s get %s' % (switch[0], switch[1]) + ' | more > %s' % wmicfile
		run_cmd(wmiccommand)
		with open(wmicfile, 'r') as infile:
			# strip down string to the required value
			q = infile.read()
			if switch[1]=='ipaddress':
				q = [i for i in q.split('"') if ' ' not in i]
			elif switch[1]=='installdate':
				q = q.split('\n')[1].rstrip()
				q = q[6:8]+'-'+q[4:6]+'-'+q[:4]+' '+q[8:10]+':'+q[10:12]+':'+q[12:14]
			else:
				q = q.split('\n')[1].rstrip()
		# append wmic value to inner list
		compspec.append(q)
	# append hosts wmic data to outer list
	computerdata.append(compspec)

# write wmic data to csv
header = ['Hostname', 'Manufacturer', 'Model', 'Service tag', 'Operating system', 'Install date', 'IP address']
with open(options.outfile, 'wb') as outfile:
	writer = csv.writer(outfile)
	writer.writerow(header)
	for row in computerdata:
		writer.writerow(row)
	
print 'Completed. View results in '+options.outfile
