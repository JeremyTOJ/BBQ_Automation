import subprocess
import os
import sys
import urllib
import re
import time



'''
minijumbo automation script
@author: yuj23
@usage: Called by bbq automation_script, with such pattern:
        "start python minijumbo_automation.py PATH_TO_DEBUGON_EXE"

It can download, install and monitor the installation process of image,
if installation succeeds, it can start start minijumbo automatically.


'''

#######################################
##             global vars           ## 
#######################################
#durl="http://10.32.112.76/patchtask/20130820-182717/debugon-NAS.exe.gz"
durl=sys.argv[1]
IMAGE="debugon-NAS.exe.gz"
SCP_PATH="C:\\Users\\Administrator\\Desktop\\Putty\\Putty\\PSCP.EXE"
PLINK_PATH="C:\\Users\\Administrator\\Desktop\\Putty\\Putty\\PLINK.EXE"
USER="root"
PASSWORD="nasadmin"
CS_IP="10.245.64.72"
TARGET_PATH="/root/abc"
PLINK="%s -ssh -l %s -pw %s %s"%(PLINK_PATH,USER,PASSWORD,CS_IP)
RESET=PLINK+" "+ "/nas/sbin/t2reset reboot -s 2"
GETREASON=PLINK+" "+ "/nas/sbin/getreason "
SCP="%s -scp  -l %s -pw %s %s %s:%s"%(SCP_PATH, USER, PASSWORD, IMAGE,CS_IP,TARGET_PATH)
PERL_PATH="C:\\Perl64\\bin\\perl.exe"
SCRIPT_NAME="konductorCLI.pl"
SERVER_NAME="10.244.116.60"
USER_NAME="Yunfei Chen"
QUEUE_NAME="Yunfei-minijumbo-test2"
START_JOB=r'%s %s --server %s -userName %s --queueName %s --queue  restart'%(PERL_PATH,SCRIPT_NAME,SERVER_NAME,USER_NAME,QUEUE_NAME)
NFS_MOUNT="cmd /c net use Z: \\\\%s\\repository"%SERVER_NAME
NFS_DEL=r"cmd /c net use Z: /del"


#######################################
##             functions             ## 
#######################################

##Download image

if os.path.exists(IMAGE):
    os.popen("cmd /c del %s"%IMAGE)

	
urllib.urlretrieve(durl, IMAGE)
    

##Send IMAGE to CS


try:
    scpout=subprocess.check_output(SCP,shell=True)
    print scpout
except Exception,err:
    print str(err)

##RESET CS

try:
    resetout=subprocess.check_output(RESET,shell=True)
    print RESET
    print resetout
except Exception,err:
    print str(err)

    
##GET RESET STATUS OF CS

    
count=0
reset_reg=re.compile(r'^(\s)*5')
while count<=100:
    if count==100:
        print "Error occurred with CS!"
        exit()
    try:
        proc2=subprocess.Popen(GETREASON, stdout=subprocess.PIPE,shell=True)
        reasonout,reasonerr=proc2.communicate()
        print GETREASON
        print reasonout
        outlist=reasonout.split('\n')
        reset_m=reset_reg.match(outlist[1])
        if reset_m:
            print "Reset Done."
            break
    except Exception,err:
        print str(err)
    time.sleep(20)

##mount nfs
##

if os.path.exists("Z:\\"):
    print "Driver Z has been mounted, will remove."
    try:
        out=subprocess.check_output(NFS_DEL, shell=True)
        print NFS_DEL
        print out
    except Exception,err:
        print str(err)
try:
    out=subprocess.check_output(NFS_MOUNT, shell=True)
    print NFS_MOUNT
    print out
except Exception,err:
    print str(err)

##Start minijumbo
## execute this command in other folder won't work
os.chdir("Z:")
os.chdir(".\\konductorCLI")

try:
    startjobout=subprocess.check_output(START_JOB,shell=True)
    print START_JOB
    print startjobout
    start=re.compile(r"Starting queue...")
    end=re.compile(r'Done!')
    if start.search(b) and end.search(b):
        print "JOB has been started."
    else:
        print "Minijumbo starts failure."
except Exception,err:
    print str(err)
