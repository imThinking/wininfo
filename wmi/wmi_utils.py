__title__ = 'wininfo'
__version__ = '0.1'
__author__ = 'ZHOU'
__license__ = 'Apache v2.0 License'

# WIN_sysutils.py  
# wrappers for windows DiskPart and WMIC utilities
# 
# copyright @ 2020 Michael George thingssanjose.com
#
# 2020-08-05  mg write the classes and standalone __main__  test program in this module.

import subprocess
import re
from tempfile import NamedTemporaryFile
'''
tempfile.NamedTemporaryFile
如果临时文件会被多个进程或主机使用，那么建立一个有名字的文件是最简单的方法。这就是NamedTemporaryFile要做的，可以使用name属性访问它的名字
'''

# WIN_testpatterns() decodes a line of output from windows utilities requests.
# iterates through a patternset list of [(regex, handlerfunc) pairs ...] 
# returns three items: 
#   1. callback fn associated with the matching regexs
#   2. count of groups (corresponding to the matched parsed fields of the input record)
#   3. groups - a list of matched strings parsed from a single out line of the utility
# Win_testpatterns() 用于将Windows输出信息进行解码
# 通过正则表达式进行迭代
def WIN_testpatterns(line,patternset):                     
        # test all patterns against the input line. 
        # Note that the order of the patterns is relevant to the interpretation; changing the pattern order will affect first match in event of multiple match patterns matching
        for (myregx,servicefn) in patternset:
            matchinfo = re.match(myregx,line)
            if matchinfo:
                kwlen = len(matchinfo.groups())
                kwgroup = matchinfo.groups()
                reportstr = None #  servicefn(kwgroup=matchinfo.groups(),kwlen=len(matchinfo.groups()))
                return servicefn, len(matchinfo.groups()), matchinfo.groups()
        # if nothing hit on a pattern
        return None,0,None 

# newtempfile() - create an application temporary file
#  (this was created for use to create DiskPart runtime script from a list of cmd lines)
# write input data to the file with or without inserted newlines
# returns name of the file created
# 创建临时文件，将命令行放入临时文件，以供diskpart命令调用，返回值为临时文件名。
def newtempfile(cmdslist, baddnewlines=False):
    # write the query to a DiskPart input text file. changed this to a TEMP file so user isn't impacted!
    diskpart_data = NamedTemporaryFile(delete=False) #"get-drives.txt"
    diskpart_data_name = diskpart_data.name 
    d03 = open (diskpart_data.name, "w")
# baddnewlines 用于判断是否需要加入'\'换行
    try:
        if baddnewlines:
            str = '\"'
            for j in cmdslist:
                str+= j+'\n'
            str +='\"'
            d03.write(str)
        else:
            for i in cmdslist:
               d03.write(i)
        d03.close()
    except:
        pass
    return diskpart_data.name


# class WIN_winutils - generic base class for invoking windows utilities via subprocess()
# normal case WMIC commands are directly sent to windows shell cmd; 
# special provision for creating a temp script file and executing Diskpart /s <tempfile> 
class WIN_winutils(object):
    (DISKPART,WMIC,SMART) = range(3)

    def __init__(self,utiltype,cmddict):

        # info about this utility instance
        self.cmddict = cmddict
        self.utiltype = utiltype 

        # system info that is collected
        self.sysdata = dict()
        self.sysdata[cmddict['infoname']] = [] 

        # utility standard output
        self.reportlines = []
        
    def process_cmd(self):

        # for diskpart requests, write cmdlines to temporary script file
        # diskpart运行时，所有参数从临时文件中读取
        if self.utiltype == WIN_winutils.DISKPART:
            fname = newtempfile(self.cmddict['cmdlist'], baddnewlines=True)
            self.cmddict['cmdline'] = "diskpart /s %s"%fname 

        self.wu_exec_proc()

        for i in self.reportlines:
            handlerfunc,ngrps,grps= WIN_testpatterns( i.decode('utf-8', 'ignore'), self.cmddict['regexes'])

            # if there's no handler, there's no post-processing defined. possible the caller just wants the raw output
            if not handlerfunc:
                continue

            # using the keys in the cmddict(), fill in the data as it is parsed
            self.groupsmatched = grps
            self.ngrps = ngrps

            # some utilities have customized handlers for fields
            if len(self.cmddict['infokeys']) == 0:
                handlerfunc( 0,0, grps )
                continue

            # a simple attempt to ignore the header report line
            if grps[0] == self.cmddict['infokeys'][0]: 
                continue 

            # generic utility output handled here
            tmpdict = dict()
            for ix,ky in enumerate(self.cmddict['infokeys']):
                # no postprocessing spec in the cmddict()
                tmpdict[ky] = handlerfunc(grps[ix], ix)  # option-specific fixup like int(value) since they're all strings after parsing


            # add an item to the list of dicts
            self.sysdata[self.cmddict['infoname']].append(tmpdict)

    def wu_getinfo(self):
        #return length & this instance key data
        return len(self.sysdata[self.cmddict['infoname']]), self.sysdata[self.cmddict['infoname']]

    # execute a subprocess 
    def wu_exec_proc(self):
        errcode = -1
        try:
            process = subprocess.Popen ( self.cmddict['cmdline'],
                shell=True, 
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin= subprocess.PIPE # ADD THIS FOR THE --noconsole or -windowed pyinstaller .exe built versions!!
                )
            #
            errcode = process.returncode
            #LessonLearned when converting the scripts to standalone .exe.
            #   https://github.com/pyinstaller/pyinstaller/wiki/Recipe-subprocess
            # if pyinstaller is invoked with pyinstaller -console  scriptblahblah.py, subprocess funcs are ok, output goes to console
            # if pyinstaller is invoked with pyinstaller -windowed or --noconsole  the executable has internal (invisible in a runtime exe) exceptions around subprocess calls
            #
            #for line in process.stdout:
            #    result.append(line)
            self.reportlines= process.communicate()[0].splitlines()
            pass
        except:
            pass
        return errcode, self.reportlines

# class WIN_wmic - create instances of various WMIC stoarage device queries. disks, bootdisk, volumes, partitions, computer product info
class WIN_wmic(WIN_winutils):
    (WMIC_BOOTDISK,WMIC_DISKS,WMIC_VOLUMES,WMIC_PARTITIONS,WMIC_CSPRODUCT) = range(0,5)

    def __init__(self, wmicquery ):
        wmic_cmds = dict()
        wmic_cmds[str(WIN_wmic.WMIC_DISKS)] =  {"cmdline":'wmic  /locale:ms_409 diskdrive list brief /format:csv', 
                                                "regexes": [('^[^,]*,([^,]*),.*PHYSICALDRIVE([0-9]+),.*,([0-9]+),([0-9]+).*$', self.diskshandler),],
                                                "infokeys":['Caption', 'DeviceID','Partitions', 'Size'],
                                                "infoname":'Disks'}
        wmic_cmds[str(WIN_wmic.WMIC_BOOTDISK)] = {"cmdline":'wmic  /locale:ms409 bootconfig list brief /format:csv ',
                                                "regexes":[('^[^,]*,([A-Z]{1}):([^,]*),.Device.Harddisk([0-9]*).Partition([0-9]*),([^,]*).*$',self.bootdrivehandler),],
                                                "infokeys":['BootDrive', 'BootFolder', 'Boot Disk ###', 'Boot Partition ###', 'Config name'],
                                                "infoname":'Boot'
                                                }
        wmic_cmds[str(WIN_wmic.WMIC_VOLUMES)] = {"cmdline":'wmic  /locale:ms409 volume list brief /format:csv ',
                                               "regexes":[('^[^,]*,([0-9]+),([0-9]+),([^,]*),([0-9]+),([^,]*),(.*)$',self.volumeshandler),],
                                               "infokeys":['Capacity', 'DriveType', 'FileSystem', 'FreeSpace', 'Label', 'Name'],
                                               "infoname":'Volumes'
                                               }
        wmic_cmds[str(WIN_wmic.WMIC_PARTITIONS)] = {"cmdline":'wmic  /locale:ms409 partition list brief /format:csv',
                                                  "regexes":[('^[^,]*,(TRUE|FALSE),([0-9]+),Disk #([0-9]+),\s+Partition\s+#([0-9]+),([0-9]+),(TRUE|FALSE),([0-9]+).*$',self.partitionshandler),],
                                                  "infokeys":['BootPartition',  'Index',   'Disk ###', 'Partition ###', 'NumberOfBlocks', 'PrimaryPartition',   'Size'],
                                                  "infoname":'Partitions'
                                                  }
        wmic_cmds[str(WIN_wmic.WMIC_CSPRODUCT)] = {"cmdline":'wmic  /locale:ms409 csproduct list brief /format:csv',
                                                  "regexes":[('^([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*).*$',self.noophandler),],
                                                  "infokeys":['Node',  'Description',  'Identifier', 'Product Name', 'Vendor', 'Version'],
                                                  "infoname":'ComputerProduct'
                                                  }
        super().__init__( WIN_winutils.WMIC, wmic_cmds[str(wmicquery)] )
        
        self.process_cmd()
        return

    def noophandler(self, xitem, ix, grplist=None):
        return xitem

    def diskshandler(self, xitem, ix, grplist=None):
        if ix == 1:
            return int(xitem)
        if ix == 2:
            return int(xitem)
        if ix == 3:
            return int(xitem)
        return xitem

    def bootdrivehandler(self,xitem,ix, grplist=None):
        if ix == 2:
            return int(xitem)
        if ix == 3:
            return int(xitem)
        return xitem

    def volumeshandler(self, xitem, ix, grplist=None):
        if ix == 0:
            return int(xitem)
        if ix == 1:
            return int(xitem)
        if ix == 3:
            return int(xitem)
        return xitem

    def partitionshandler(self, xitem, ix, grplist=None):
        if ix == 1:
            return int(xitem)
        if ix == 2:
            return int(xitem)
        if ix == 3:
            return int(xitem)
        if ix == 4:
            return int(xitem)
        if ix == 6:
            return int(xitem)
        return xitem


# diskpart - utility class ## parse disks, volumes and partitions into dicts
# 调用diskpart命令
class WIN_diskpart(WIN_winutils):
    (DISKPART_LISTDISKS,DISKPART_DISKS,DISKPART_SETUNIQUEID,DISKPART_GETUNIQUEID) = range(0,4)

    # defaults, no programming provision yet for these format options. it can be done.
    FSTYPE = 'NTFS'
    FSMODE = 'QUICK'
    FSCOMPRESS = ''
    FSLABEL = 'SSD-00000'

    def __init__(self, diskpartquery, targetnumber=-1, uniqueidstr="" ):
        dp_cmds = dict()
        # 磁盘列出 list disk
        dp_cmds[str(WIN_diskpart.DISKPART_LISTDISKS)] = {"cmdlist": ['list disk',],
                                                    "regexes": [('^.*(Disk)\ ([0-9]+)\s*(.{13})\s*([0-9]*\ (?:GB|MB|KB|TB|B))\s*([0-9]*\ (?:GB|MB|KB|TB|B))\s{2}(.{3})\s{2}(.{1,3}).*$', self.diskdriveunit),
                                                    ],
                                                    "infokeys":[],
                                                    "infoname":'Disks', 
                                                    "scriptlines": []}
        # 分区列出 list partitions
        dp_cmds[str(WIN_diskpart.DISKPART_DISKS)] =  {"cmdlist":['select disk %d'%targetnumber,'detail disk','list partition'], 
                                                    "regexes": [ ('^.*(Disk)\ ([0-9]+)\s*(.{13})\s*([0-9]*\ (?:GB|MB|KB|TB|B))\s*([0-9]*\ (?:GB|MB|KB|TB|B))\s{2}(.{3})\s{2}(.{1,3}).*$', self.diskdriveunit ),
                                                            ('^\s*(.*):\s*(.*)',self.diskitem),
                                                            ('^.*(Volume){1}\ ([0-9\ ]{3})[\ ]{2}([A-Z\ ]{3})[\ ]{2}(.{11})\s*(NTFS|FAT32|exFAT|EXFAT)\s*(Partition|Removable)\s*([0-9]*\s*(?:GB|MB|KB|TB|B))\s{2}(\S*)\s*(\S*).*', self.diskvolume),
                                                            ('^.*(Partition){1}\ ([0-9\ ]{3})[\ ]{2}(.{11})\s*([0-9]*\s*(?:GB|MB|KB|TB|B))\s*([0-9]*\s*(?:GB|MB|KB|TB|B)).*', self.diskpartition),
                                                            ],
                                                    "infokeys":[],
                                                    "infoname":'Disks', 
                                                    "scriptlines":[]}
        # 获取GUID
        dp_cmds[str(WIN_diskpart.DISKPART_GETUNIQUEID)] = {"cmdlist":['rescan','select disk %d'%targetnumber,'uniqueid disk'],
                                                            "regexes":[('^.*(Disk ID: {)([0-9A-F\-]{32})([0-9A-F]{4})}.*$', self.stdguid ), 
                                                                       ('^.*(Disk ID: )([0-9A-F]{8}).*$', self.serno ), ],
                                                            "infokeys":[],
                                                            "infoname":'UniqueID',
                                                            "scriptlines":[] }
        # 设置GUID
        dp_cmds[str(WIN_diskpart.DISKPART_SETUNIQUEID)] = {"cmdlist":['select disk %d'%targetnumber,'uniqueid disk id=%s'%uniqueidstr, 'online disk'],
                                                            "regexes":[ ('^.*(DiskPart successfully onlined the selected disk).*$', self.onlinesuccess ), # b'The specified identifier is not in the correct format.'b'Type the identifier in the correct format:'
                                                                         ('^.*(This disk is already online.).*$', self.onlinealready )
                                                                       ],
                                                            "infokeys":[],
                                                            "infoname":'UniqueID',
                                                            "scriptlines":[] }

        super().__init__( WIN_winutils.DISKPART, dp_cmds[str(diskpartquery)] )
        self.targetnumber = targetnumber
        self.online = False # for the UUID update/ ONLINE operation
        self.formatstate = [] # for format progress msgs
        self.diskdicts = []
        self.diskdetails = dict()
        self.diskdetails['Disk ###'] = targetnumber
        self.volumedicts = []
        self.partitiondicts = [] 
        self.process_cmd()
        return

    # handler for a GUID line in the report
    def stdguid(self, gitem,gix, grplist=None):
        self.GUID_first32 = grplist[1].strip()
        self.GUID_last4 = grplist[2].strip()
        self.GUID = self.GUID_first32 + self.GUID_last4

    # handler for a MBR-style GUID line in the report
    def serno(self, gitem,gix, grplist=None):
        self.GUID = grplist[1]

    # handler for disk online operation part of the UUID change sequence
    def onlinesuccess(self, gitem, gix, grplist):
        self.onlinesuccess = True
        self.online = True

    # handler for disk online operation part of the UUID change sequence
    def onlinealready(self, gitem, gix, grplist):
        self.onlinealready = True
        self.online = True

    # handler for disk unit summary lines from List Disk
    def diskdriveunit(self, gitem,gix, grplist=None):
        tmpdisk = dict()
        try:
            tmpdisk['Disk ###'] = grplist[1]
            tmpdisk['Status']  = grplist[2].strip()
            tmpdisk['Size'] = grplist[3].strip()
            tmpdisk['Free'] = grplist[4].strip()
            tmpdisk['Dyn'] = grplist[5].strip()
            tmpdisk['Gpt'] = grplist[6].strip()
            self.diskdicts.append(tmpdisk)
        except:
            pass

    # handler for each disk detail line from Detail Disk
    def diskitem(self,gitem,gix, grplist=None):
        try:
            self.diskdetails[grplist[0]] = grplist[1]
        except:
            pass

    # handler for each disk partition line from Detail Disk
    def diskpartition(self, xitem, ix, grplist=None):
        tmppart = dict()
        tmppart['Disk ###'] = self.targetnumber 
        tmppart['###'] = grplist[1]
        tmppart['Type'] = grplist[2]
        tmppart['Size'] = grplist[3]
        tmppart['Offset'] = grplist[4]
        self.partitiondicts.append(tmppart)

    # handler for each disk volume line from Detail Disk
    def diskvolume(self, xitem, ix, grplist=None):
        tmpvol  = dict()
        tmpvol['Disk ###'] = self.targetnumber
        tmpvol['Volume ###'] = grplist[1].strip()
        tmpvol['Ltr'] = grplist[2].strip()
        tmpvol['Label'] = grplist[3].strip()
        tmpvol['Fs'] = grplist[4].strip()
        tmpvol['Type'] = grplist[5].strip()
        tmpvol['Size'] = grplist[6].strip()
        tmpvol['Status'] = grplist[7].strip()
        tmpvol['Info'] = grplist[8].strip()
        self.volumedicts.append(tmpvol)

    # updategui() is a special utility function to modify GUID
    # in an instance of WIN_diskpart( WIN_diskpart.DISKPART_GETUNIQUEID ... ), call this method to modify the GUID value with a caller-specified offset
    # this returns a guid string which is formatted for use in a new WIN_diskpart.DISKPART_SETUNIQUEID instance/ operation
    def updateguid(self, addtoguid):
        try:
            if self.GUID: 
                last4 = self.GUID[-4:]
                gval = int(last4,16) + addtoguid
                newguid = '%s%04X'%(self.GUID[0:-4],gval)
                return newguid
        except:
            raise Exception("GUID update request must be made with instance from GETUNIQUEID operation")

    def format0(self, xitem, ix, grplist=None):
        self.formatstate.append(grplist[0])

    def format1(self, xitem, ix, grplist=None):
        self.format0(xitem,ix,grplist)

    def format2(self, xitem, ix, grplist=None):
        self.format0(xitem,ix,grplist)


if __name__ == '__main__' :
    # Test program testing / demonstrating Windows WMIC and DiskPart commands
    # note that Format example will fail due to illegal drive spec in the instantiation. 
    # it FORMATs the disk! the code with care 
    print('** WIN_SysUtils.py TEST PROGRAM **')
    
    # example of creating/writing a temp file
    fname = newtempfile(['line1','line2','line3'], baddnewlines=True)
    print('Temp file with some data at: ', fname)
    # examples of creating/writing a temp file
    fname11 = newtempfile(['l1\n', 'l2\n','l3\n'])
    print('Temp file with some data at: ', fname11)

    print('\n\nDiskPart information dump... \n')
    # DiskPart example collecting all of the system disks, volumes, partitions; AND change uniqueid, AND format a target volume
    diskinfx = WIN_diskpart(WIN_diskpart.DISKPART_LISTDISKS)
    disk_numbers = []
    for i in diskinfx.diskdicts:
        print('----- Disk ----->  ', i)
        diskinf = WIN_diskpart(WIN_diskpart.DISKPART_DISKS, int(i['Disk ###']))
        disk_numbers.append(int(i['Disk ###']))
        print('------Disk Details', diskinf.diskdetails)
        for j in diskinf.volumedicts:
            print('-----Volumes', j)
        for j in diskinf.partitiondicts:
            print('-----Partitions', j)
        diskuuid = WIN_diskpart(WIN_diskpart.DISKPART_GETUNIQUEID, int(i['Disk ###']))
        print('-----Disk GUID', diskuuid.GUID)

    # WARNING test the GUID update - this is very specific to MY SYSTEM/ DISK #2!!
    diskuuid2 = WIN_diskpart(WIN_diskpart.DISKPART_GETUNIQUEID, 2)
    if 2 in disk_numbers:
        print(diskuuid2.GUID)
        newguidstr = diskuuid2.updateguid(5)
        if False: # DISABLE THE GUID modification so noone messes up a system configuration
            diskuuid3 = WIN_diskpart(WIN_diskpart.DISKPART_SETUNIQUEID, 2, newguidstr)
        else:
            print("DISABLED TEST CODE:   WIN_diskpart(WIN_diskpart.DISKPART_SETUNIQUEID, 2, newguidstr)")

    # WARNING *** FORMAT A VOLUME *** THIS WILL WIPE ANY DATA FROM THE TARGET DISK!!
    diskfmt = WIN_diskpart(WIN_diskpart.DISKPART_FORMAT, 2, "----invalid text here ---valid drive letter target required F:")
    print('--Format output-- ',diskfmt.formatstate)


    # demonstrate the wmic utility class with instances for boot device, disks, volumes, partitions, product information.
    print('\n\nWMIC information dump... \n')
    # the boot disk info
    lb, Wbootinf = WIN_wmic(WIN_wmic.WMIC_BOOTDISK).wu_getinfo()
    for i in Wbootinf :
        print('Boot',i)

    # all the disks
    ld, Wdiskinf = WIN_wmic(WIN_wmic.WMIC_DISKS).wu_getinfo()
    for i in Wdiskinf :
        print('disk',i)

    # all the volumes
    lv, Wvolinf = WIN_wmic(WIN_wmic.WMIC_VOLUMES).wu_getinfo()
    for i in Wvolinf :
        print('volume',i)

    # all the partitions
    lp1, Wpartinf = WIN_wmic(WIN_wmic.WMIC_PARTITIONS).wu_getinfo()
    for i in Wpartinf :
        print('partition',i)

    # the computer product info
    lp2, Wprodinfo = WIN_wmic(WIN_wmic.WMIC_CSPRODUCT).wu_getinfo()

    print('PRODUCT INFORMATION', Wprodinfo )
    print('** WIN_SysUtils.py TEST PROGRAM COMPLETE**')
