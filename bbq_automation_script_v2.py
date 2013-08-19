# -*- coding: cp936 -*-
import os
import re
import sys
import urllib
from sgmllib import SGMLParser
import zipfile
import smtplib
import ftplib
import subprocess
from email.mime.text import MIMEText
from email.Header import Header
from email.MIMEText import MIMEText
from email.MIMEMultipart import MIMEMultipart
import logging
import time
import difflib
import base64
import email.mime.text
import email.utils
import datetime
from ftplib import FTP
import paramiko



##############################################
##
## Global Variables
##
##############################################


##Format the log file

filename="%Y_%m_%d_%H_%M_%S"
logger = logging.getLogger()
logfile = "log_"+str(time.strftime(filename)) +".txt"
hdlr = logging.FileHandler(logfile)
formatter = logging.Formatter('==========%(funcName)s==========%(asctime)s\t[%(levelname)s]\t\t%(message)s')
hdlr.setFormatter(formatter)
logger.addHandler(hdlr)
logger.setLevel(logging.DEBUG)



### There are four kinds of logs in this program.
###logging.info('infomation')
###logging.debug('debug info')
###logging.warn('warning info')
###logging.error('error info')

CONF={"TYPE":"Checked",
      "MLU_FREE":"",
      "MLU_CHECKED":"",
      "DEDUP_CHECKED":"",
      "DEDUP_FREE":"",
      "MLU_IMAGE":"",
      "DED_IMAGE":"",
      "ndustr":"",
      "MLUSANITYZIP":"MLUSanity.zip",
      "SANITYFOLDER":"OffArraySanity",
      "SPA":"10.109.68.150",
      "SPA_USER":"nasadmin",
      "SPA_PW":"nasadmin",
      "SPB":"10.109.68.151",
      "SPB_USER":"nasadmin",
      "SPB_PW":"nasadmin",
      "HOST":"10.109.81.17",
      "HOST_USER":"Administrator",
      "HOST_PW":"clariion!",
      "patchtask":"http://10.32.112.76/patchtask/",
      "REVISION":"",
      "BASE":"D:\\yuj23\\MLUSanity\\test",
      "TIMESTAMP":"",
      "DOWNLOADURL":"",
      "BUILDSTATUS":"build-status.txt",
      "MSG":"msg.txt"
      }
##CONF["SPA_USER"]
##CONF["SPA_PW"]
##CONF["SPB_USER"]
##CONF["SPB_PW"]
SPA_CMD="naviseccli -user %s -password %s -scope 0 -h %s"(CONF["SPA_USER"],CONF["SPA_PW"],CONF["SPA"])
SPB_CMD="naviseccli -user %s -password %s -scope 0 -h %s"(CONF["SPB_USER"],CONF["SPB_PW"],CONF["SPB"])



##############################################
##
## Functions
##
##############################################

##Get info of array, decide which bundle should be downloaded

def GetArrayInfo():
    revision={}
    logging.info("Getting the array info Start...")
    flag={CONF["SPA"]:False,CONF["SPB"]:False}
    p=re.compile(r'^Revision:(?:\s)*(\d*)\.(\d*)\.(\d*)\.(\d*)\.(\d*)')
    for i in (CONF["SPA"],CONF["SPB"]):
        process1 = subprocess.Popen("naviseccli -user nasadmin -password nasadmin -scope 0 -h %s getagent"%i,
                                    shell=True, stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        agentlist=process1.stdout.readlines()
        
        for line in agentlist:
            linestr=line.rstrip()
            mrevision=p.match(linestr)
            if mrevision:
                 revision[i]= '.'.join(mrevision.groups())
                 flag[i]=True
                 break   
    
    if revision[CONF["SPA"]]==revision[CONF["SPB"]] and revision[CONF["SPA"]]!="":
        
        CONF["REVISION"]=revision[CONF["SPA"]]
        if CONF["REVISION"].split('.')[3]=="3":
              CONF["TYPE"]="Free"
        logging.info("Getting the array info End...")
    else:
        logging.error("Array was down!")
        exit()

##fetch build status and other files

class URLLister(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.urls=[]
    def start_a(self, attrs):
        href=[v for k,v in attrs if k=='href']
        if href:
            self.urls.extend(href)

              
def FetchUrl():
    ##Fetch the second link of target url
    ## As for the validity of this link, i will do some judge later
    logging.info("Start Fetching Url...")
    sock= urllib.urlopen(CONF["patchtask"])
    htmlSource = sock.read()
    parser=URLLister()
    parser.feed(htmlSource)
    sock.close()
    parser.close()
    downloadurl=parser.urls[7]
    
    logging.info("Fetching Url Succeeded...")
    return downloadurl

def ChangeDir(dirname):
    logging.info("Start making dir...")
    os.chdir (CONF["BASE"])
    
    if not os.path.exists (dirname):
        os.mkdir (dirname)
    
    os.chdir(dirname)
    logging.info("End making dir...")

def DownloadFiles(targeturl):
    logging.info("Download files started..")
    sock= urllib.urlopen(targeturl)
    htmlSource = sock.read()
    statusflag=False
    parser=URLLister()
    parser.feed(htmlSource)
    sock.close()
    parser.close()
    p_build=re.compile(CONF["BUILDSTATUS"])
    if CONF["TYPE"]=="Free":
        p_mlu=re.compile(r'MLUEngine-(.)*_free.upf')
        p_dedup=re.compile(r'DeduplicationEngine-(.)*_free.upf')
    elif CONF["TYPE"]=="Checked":
        p_mlu=re.compile(r'MLUEngine-(.)*_checked.upf')
        p_dedup = re.compile(r'DeduplicationEngine-(.)*_checked.upf')
    p_zip=re.compile(CONF["MLUSANITYZIP"])
    p_msg=re.compile(CONF["MSG"])
    flag=[False]*5
    for url in parser.urls:
        m = re.match(CONF["BUILDSTATUS"],url)
        m_mlu=p_mlu.match(url)
        m_dedup=p_dedup.match(url)
        m_zip=p_zip.match(url)
        m_msg=p_msg.match(url)
        if m:
            flag[0]=True
        if m_mlu:
            flag[1]=True
            CONF["MLU_IMAGE"]=url
        if m_dedup:
            flag[2]=True
            CONF["DED_IMAGE"]=url
        if m_zip:
            flag[3]=True
        if m_msg:
            flag[4]=True
    for i in range(0,5):
        if flag[i]==False:
            logging.error("Download Fail, exit code: %d"%i)
            exit()
    downloadlist=[CONF["BUILDSTATUS"],CONF["MLU_IMAGE"],CONF["DED_IMAGE"],
                  CONF["MLUSANITYZIP"],CONF["MSG"]]
    for item in downloadlist:
        if not os.path.exists('.\\%s'%item):
            urllib.urlretrieve(CONF["DOWNLOADURL"]+"/"+item,item)
    else:
        logging.info("%s Occurs, no need to download"%item)

    for item in downloadlist:
        if not os.path.exists('.\\%s'%item):
            logging.error("Download Error Occurs For %s"%item)
            exit()
        else:
            logging.info("Download for %s complete..."%item)
            
    logging.info("Download files passed...")

def CheckBuildStatus():
    logging.info("Check the status started...")
    lines = open(".\\%s"%CONF["BUILDSTATUS"],'r').readlines()
    for line in lines:
        linelist=line.rstrip().split(" ")
        if linelist[1]=="fail":
            logging.error("The build of %s failed!"%linelist[0])
            exit()
    logging.info("Check the status end...")

    
def InstallImage():
    logging.info("Install the image Start...")
    
    INSTALL="%s ndu -messner -install %s %s  -skiprules -disruptive "%\
             (SPA_CMD,CONF["DED_IMAGE"],CONF["MLU_IMAGE"])
    pro=subprocess.Popen(INSTALL,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    stdout_value, stderr_value = pro.communicate('y')
    if stderr_value:
        logging.error("Install the image failed...")
    logging.info("Install the image End...")
    



    
def TestInstallStatus():
    logging.info("Start to check if install finishes....")
    
    Time_out=0
    while True:
        Time_out+=1
        if Time_out>60:
            logging.error("%s is down.."%CONF["SPA"])
            exit()
        try:
            ret = subprocess.check_output("%s ndu -status"%SPA_CMD)
            logging.info(ret)
            m   = re.findall(r"Is Completed:\W+([YES]+)", ret)
            if len(m) > 0:
                break
        except Exception, err:
            logging.info(str(err))
            pass
        time.sleep(60)
    Time_out=0  
    while True:
        Time_out+=1
        if Time_out>10:
            logging.error("%s is down.."%CONF["SPB"])
            exit()
        try:
            ret = subprocess.check_output("%s ndu -status"%SPB_CMD)
            logging.info(ret)
            m   = re.findall(r"Is Completed:\W+([YES]+)", ret)
            if len(m) > 0:
                break
        except Exception, err:
            logging.info(str(err))
            pass
        time.sleep(60)
    logging.info("Bothe SPs has been installed correct image....")

def CommitImage():
    logging.info("Start to commit image...")
    os.popen("%s ndu -commit  MLUEngine DeduplicationEngine"%SPA_CMD)
    logging.info("Finish to commit image...")


def unzipfile(zipfilename):
    logging.info("Unzip files Start...")
    f=zipfile.ZipFile(zipfilename,'r')
    for file in f.namelist():
        f.extract(file,".")
    logging.info("Unzip files completed...")


def ModifyConfig():
    logging.info("Modifying the config file Start...")
    if os.path.exists(CONF["SANITYFOLDER"]):
        os.chdir(CONF["SANITYFOLDER"])
        base=os.getcwd()
    else:
        logging.error( "The target dir doesn't exist!")
        exit()
    cur_list = os.listdir(base)
    for file in cur_list:
        if file=="Config.txt":
            CONF_PATH=base+"\\"+file
    lines = open(CONF_PATH).readlines()
    line_to_be_replaced=lines[1:6]
    Add_list=[CONF["SPA"],CONF["SPB"],"nas","nas",CONF["HOST"]]
    count=0
    for line in line_to_be_replaced:
        linesp = line.split("=")
        for i in range(len(Add_list)):
            if count==i:
                linesp[1]=Add_list[i]+linesp[1]
        count+=1
        line='='.join(linesp)
        line_to_be_replaced[count-1]=line
    
    for i in range(1,6):
        lines[i]=line_to_be_replaced[i-1]

    f = open(CONF_PATH, 'w')
    f.writelines(lines)
    f.close()
    logging.info("Modifying the config file End...")


def RebootHost():
    PING=".\\ping.txt"
    timestamp=0
    while(timestamp<=40):  ## TIMEOUT : 10 minutes
        os.system("cmd /c shutdown -r -m \\%s -t 4 > %s"%(CONF["HOST"],PING))
        timestamp+=1
        time.sleep(15)
        lines=open(PING,"r").readlines()
        p=re.compile(r"(\s)*Minimum(\s)*=(\s)*((\d)*)ms")
        m=p.match(lines[-1])
        if m:
            logging.info("Host has been rebooted...")
            return
        else:
            continue

    logging.error("Host can't boot up!")
    exit()

def ExecuteSanity():
    logging.info("start MLUSanity...")
    PERL_FILE="MLUSanity.pl"
    
    base=os.getcwd()
    proc1=subprocess.Popen("perl %s\\%s\\%s"(CONF["BASE"],CONF["SANITYFOLDER"],PERL_FILE),stdin=subprocess.PIPE \
                           ,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    proc1.communicate("y")
    filelist=os.listdir(base)
    p=re.compile(r"log(.)*\.txt")
    flag=False
    sanitylogfile=""
    for i in filelist:
        m=p.match(i)
        if m:
            flag=True
            sanitylogfile=i
            break
    if flag:
        ##log=open(logfile,'r')
        lines=open(sanitylogfile,"r").readlines()
        p2=re.compile(r'(.)*(\s)*PASSED(\s)*')
        m2=p2.match(lines[-5])
        if m2:
            failtag=False
            
            logging.info("Sanity Passed...")
        else:
            logging.info("Sanity Failed...")
            failtag=True
    else:
        failtag=True
        logfile=""
        logging.error("No log file found...")
    return failtag,sanitylogfile

def UploadFile(file):
    ftp = FTP()
    
    timeout = 30
    port = 21
    
    ftp.connect('10.32.112.79',port,timeout)
    ftp.login('nasadmin','nasadmin')
    ftp.cwd('./public_html')
    ftp.storbinary('STOR '+logfile, open(path,'rb'))
    ftp.quit()

def GetDiff():
    if os.path.exists (CONF["BASE"]+"former.txt"):
        text1=open(CONF["BASE"]+"former.txt","r").readlines()
    text2=open("msg.txt",'r').readlines()[2]
    d = difflib.Differ()
    diff = d.compare(text1, text2)
    ##here we will match the ones include patches
    p=re.compile(r'\+(\s)*(\S)+(\s)*')
    flag=False
    difflist=[]
    dl=list(diff)
    
    for i in dl:
        istrip=i.rstrip()
        m=p.match(istrip)
        
        if m:
            difflist.append(i)
            flag=True
    if flag:
        print difflist
    else:
        print "no diff"
            

    
    ##print text2
    if flag:
        if len(difflist)==1:
            print "1"
            realmessage=base64.decodestring(text2)+"<br>"+str(len(difflist))\
                     +' new patch in:'+"<br>"\
                 +"</table><p/><table border=\"1\">"+difflist[0][1:]+"</table>"
        else:
            print "2"
            realmessage1=base64.decodestring(text2)+"<br>"+str(len(difflist))\
                     +' new patches in:'+"<br>"\
                     +"</table><p/><table border=\"1\">"
            i=0
            realmessage=realmessage1
            while i<len(difflist):
                realmessage=realmessage+difflist[i][1:]
                i+=1
            realmessage+="</table>"
        
    else:
        print "3"
        realmessage= base64.decodestring(text2)+"<br>No new patch in.</br>"
    return realmessage



def SendMail(sanityflag,content):
    if sanityflag==False:
        subject="MLUSanity on %s Passed"%date.today()
    else:
        subject="MLUSanity on %s Failed"%date.today()
    print subject
    
    print content
    mailTo="Jeremy.Yu@emc.com"
    msg = email.mime.text.MIMEText(content,'html','utf-8')
    msg['To'] = email.utils.formataddr(('Recipient', mailTo))
    msg['From'] = email.utils.formataddr(('Jeremy.Yu', mailTo))
    msg['Subject'] = subject
    server = smtplib.SMTP(host='mailhub.lss.emc.com', port=25)
    server.sendmail(mailTo, [mailTo], msg.as_string())

    

    
if __name__=="__main__":
    GetArrayInfo()
    turl=FetchUrl()
    CONF["TIMESTAMP"]=turl[:-1]
    CONF["DOWNLOADURL"]=CONF["patchtask"]+"20130814-145624"##CONF["TIMESTAMP"]
    ChangeDir(turl[:-1])
    DownloadFiles(CONF["DOWNLOADURL"])
    CheckBuildStatus()
    InstallImage()
    TestInstallStatus()
    CommitImage()
    unzipfile(CONF["MLUSANITYZIP"])
    ModifyConfig()
    RebootHost()
    isSanityFail, SanityLog=ExecuteSanity()
    UploadFile(SanityLog)
    message=GetDiff()
    SendMail(isSanityFail,message)

