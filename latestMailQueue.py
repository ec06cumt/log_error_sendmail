#!/usr/bin/python
# -*- coding:utf-8 -*-
#author:liugao,516587331@qq.com
#desc: read config to send mail by python
#created on 2016/04/25

import sys,os  
import ConfigParser 
import linecache
import math

import signal
import time
import re
from multiprocessing import Process,Queue,Pool
import multiprocessing
#from multiprocessing import Process,Queue
 
import smtplib  
from email.mime.text import MIMEText  
from email.header import Header

#strPattern='\[(.*)\]\s+<(.*?)>\s+[Ff]ailed to decode(.*?)'
#logZoneName = "GameZoneServer_"
#logPostfix = ".log"
#dateFormat = '%Y-%m-%d'

#
g_strGlobal = "Global"
g_strInfoSize = "InfoSize"
g_strMonSize = "servermonitor"
g_strUserInfo = "UserInfo_%d"
g_UsrName="Username"
g_strPwd="Password"
g_strStmp="MailStmp"
g_strMailinfo="MailInfo_%d"
g_strFrom="From"
g_strTo="To"
g_strEncoding="Encoding"
g_strServerinfo="ServerInfo_%d"
g_strServerID="ServerID"
g_strOnceSendlins="OnceSendLines"
g_strLoginfo="logInfo_%d"
g_strLogPath = "LogPath"
g_strLogName= "LogName"
g_strDateFormat= "DateFormat"
g_strLogPostfix= "LogPostfix"
g_strOnceReadlines= "OnceReadLines"
g_strHasReadlines= "hasreadlines"
g_strRegpattern= "RegPattern"
g_strHasReadDate= "hasreaddate"



#input msg into Queue
def write(q,lock,linetext):
	if linetext:
		lock.acquire() #add lock
		q.put(linetext)
		lock.release() #release lock

#you can define your email strategy with mutiprocess.
#for some reason,some email service providers might forbit your email address,
#so you had to use serval email address.
#lineline:[4](index)[10](linenum)
def read(q,list_mailobj,InfoSize,list_indexlinenum,cfgobj):
	iCount = 0
	bSendMail = 0
	while True:
		index = iCount % InfoSize
		iGetCount = 0
		strContext = ''
		time.sleep(10)
		print "read"
		MaxSendlines = list_mailobj[index].getSendLines()
		bSendMail = 0
		while not q.empty():
			
			#set read line limited,so that send many lines by one email  (add on 2016/04/28 by liugao)
			lineline = q.get(False)
			if lineline:
				iIndex = int(lineline[0:4])
				iLineNum = int(lineline[4:14])
				print iIndex,iLineNum
				#write linenum
				if iLineNum > list_indexlinenum[iIndex]:
					list_indexlinenum[iIndex] = iLineNum + 1
				lineline = lineline[14:]
				iGetCount += 1
				strContext += lineline
			else:
				print 'context is null'
			#iGetCount reach max sendlines ,then send mail right now and sleep some seconds (add on 2016/04/28 by liugao)
			#
			#print "Read PID:"+str(os.getpid())+"index:"+str(index) + "now:"+str(iGetCount)+"sendlines:"+str(MaxSendlines)
			if iGetCount == int(MaxSendlines):
				try:
					list_mailobj[index].setsubject('Server Error')
					linelinetext = "ServerID: " + list_mailobj[index].getSeverID() + "\n"+ strContext + "\nnow :" +str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
					list_mailobj[index].settext(linelinetext)
					list_mailobj[index].sendmail()
					list_mailobj[index].clearContext()
					linelinetext = ''
					bSendMail = 1
				except Execption,e:
					bSendMail = 0
					print str(e)
					
				#print "####################:",str(bSendMail)
				if bSendMail:
					for i in range(len(list_indexlinenum)):
						DateFormat=cfgobj.get(g_strLoginfo%i,g_strDateFormat)
						strNow = str(time.strftime(DateFormat,time.localtime(time.time())))
						cfgobj.setWrite(g_strLoginfo%i,g_strHasReadDate,strNow)
						cfgobj.setWrite(g_strLoginfo%i,g_strHasReadlines,str(list_indexlinenum[i]))
				else :
					print "else list_indexlinenum",len(list_indexlinenum)
				#print "max:",iGetCount
				iGetCount = 0	
				strContext = ''
				#wait 10s and send mail
				time.sleep(10)
				break

		# if iGetCunt less oncesendlines and queue is empty
		if iGetCount > 0 and iGetCount < int(MaxSendlines):
			# send mail rightnow
			try:
				list_mailobj[index].setsubject('Server Error')
				linelinetext = "ServerID: " + list_mailobj[index].getSeverID() + "\n"+ strContext + "\nnow :" +str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
				list_mailobj[index].settext(linelinetext)
				list_mailobj[index].sendmail()
				list_mailobj[index].clearContext()
				linelinetext = ''
				bSendMail = 1
			except Execption,e:
				bSendMail = 0
				print str(e)
				
			#print "####################:",str(bSendMail)
			if bSendMail:
				for i in range(len(list_indexlinenum)):
					DateFormat=cfgobj.get(g_strLoginfo%i,g_strDateFormat)
					strNow = str(time.strftime(DateFormat,time.localtime(time.time())))
					cfgobj.set(g_strLoginfo%i,g_strHasReadDate,strNow)
					cfgobj.setWrite(g_strLoginfo%i,g_strHasReadlines,str(list_indexlinenum[i]))
			else :
				print "else list_indexlinenum",len(list_indexlinenum)
			
			#print "other:",iGetCount,MaxSendlines
			iGetCount = 0
			strContext = ''

		iCount += 1

class ReadConf:
	def __init__(self,config_file_path):
		self.path = config_file_path
		self.cf = ConfigParser.ConfigParser()
		try:
			self.cf.read(self.path)
		except:
			print 'read config file failed'
			sys.exit(1)
			
	def checkSection(self):
		if not self.cf.has_section(g_strGlobal):
			return False
		if not self.cf.has_option(g_strGlobal,g_strInfoSize):
			return False
		if not self.cf.has_option(g_strGlobal,g_strMonSize):
			return False
			
		infosize = self.cf.getint(g_strGlobal,g_strInfoSize)
		monitorsize = self.cf.getint(g_strGlobal,g_strMonSize)
		print infosize,monitorsize
		for i in range(infosize):
			if not self.cf.has_section(g_strUserInfo%i):
				print "has no %s"%g_strUserInfo
				return False
			if not self.cf.has_option(g_strUserInfo%i,g_UsrName):
				print "has no %s"%g_UsrName
				return False
			if not self.cf.has_option(g_strUserInfo%i,g_strPwd):
				print "has no %s"%g_strPwd
				return False
			if not self.cf.has_option(g_strUserInfo%i,g_strStmp):
				print "has no %s"%g_strStmp
				return False
			
			if not self.cf.has_section(g_strMailinfo%i):
				print "has no %s"%g_strMailinfo
				return False
			if not self.cf.has_option(g_strMailinfo%i,g_strFrom):
				print "has no %s"%g_strFrom
				return False
			if not self.cf.has_option(g_strMailinfo%i,g_strTo):
				print "has no %s"%g_strTo
				return False
			if not self.cf.has_option(g_strMailinfo%i,g_strEncoding):
				print "has no %s"%g_strEncoding
				return False
				
			if not self.cf.has_section(g_strServerinfo%i):
				print "has no %s"%g_strServerinfo
				return False
			if not self.cf.has_option(g_strServerinfo%i,g_strServerID):
				print "has no %s"%g_strServerID
				return False
			if not self.cf.has_option(g_strServerinfo%i,g_strOnceSendlins):
				print "has no %s"%g_strOnceSendlins
				return False
		print "check mail info success"
		for j in range(monitorsize):
			if not self.cf.has_section(g_strLoginfo%j):
				print "has no %s,%d"%(g_strLoginfo,j)
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strLogPath):
				print "has no %s"%g_strLogPath
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strLogName):
				print "has no %s"%g_strLogName
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strDateFormat):
				print "has no %s"%g_strDateFormat
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strLogPostfix):
				print "has no %s"%g_strLogPostfix
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strOnceReadlines):
				print "has no %s"%g_strOnceReadlines
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strHasReadlines):
				print "has no %s"%g_strHasReadlines
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strRegpattern):
				print "has no %s"%g_strRegpattern
				return False
			if not self.cf.has_option(g_strLoginfo%j,g_strHasReadDate):
				print "has no %s"%g_strHasReadDate
				return False
		return True
	
	def get(self,field,key):
		result=""
		try:
			result = self.cf.get(field,key)
		except:
			result=""
		return result;
	def getInt(self,field,key):
		iResult = 0
		try:
			iResult = self.cf.getint(field,key)
		except:
			iResult = 0
		return iResult
	def set(self,section,option,value):
		try:
			self.cf.set(section,option,value)
		except Exception,e:
			print str(e)
	
	def setWrite(self,section,option,value):
		try:
			self.cf.set(section,option,value)
			print self.cf.get(section,option)
			self.cf.write(open(self.path,'w'))
		except Exception,e:
			print str(e)
		
		
		
		
class MailHelper:
	def __init__(self,Subject,Username,Pwd,Stmp,From,To,ServerID,Encoding,OnceSendLines):
		self.subject = Subject
		self.username = Username
		self.pwd = Pwd
		self.stmp = Stmp
		self.sender = From
		self.recevier = To
		self.encoding = Encoding
		self.ServerID = ServerID
		self.onceSendLines = OnceSendLines
		
	def getSendLines(self):
		return self.onceSendLines
		
	def getSubject(self):
		return self.subject
		
	def getUsername(self):
		return self.username
	
	def getPwd(self):
		return self.pwd
		
	def getSeverID(self):
		return self.ServerID
		
	def clearContext(self):
		self.text = ''
		self.subject=''
		
	def settext(self,strText):
		self.text = strText
		
	def setsubject(self,strSubject):
		self.subject = strSubject
	
	def sendmail(self):
		msg = MIMEText(_text=self.text, _charset=self.encoding) #encode using utf-8
		msg['Subject'] = Header(self.subject, self.encoding) 
		msg['From'] = self.sender
		msg['To'] = self.recevier 
		try:  
			smtp = smtplib.SMTP()  
			smtp.connect(self.stmp)  
			smtp.ehlo()  
			smtp.starttls()  
			smtp.ehlo()  
			smtp.set_debuglevel(1)  
			smtp.login(self.username, self.pwd)  
			listRecevier = self.recevier.split(',')
			smtp.sendmail(self.sender, listRecevier, msg.as_string())
		except:
			#smtp.close()
			self.text = ''
			self.subject=''
			print "Send mail failed"
		smtp.quit()

#read log file per 5s
class MonitorLog:
	def __init__(self,index,OnceReadLines,zoneLogPath,contentQueue,lock,ReadLines):
		self.index = index
		self.linespilte = OnceReadLines
		self.logZonePath = zoneLogPath
		self.canSend = 0
		self.dateFormat = ''
		self.logZoneName = ''
		self.logPostfix = ''
		self.contentQueue = contentQueue
		self.lock = lock
		self.regPattern = ''
		self.readlines = ReadLines
	
	def setRegPattern(self,strPattern):
		self.regPattern = strPattern
	#send mailor not
	def setSendMailFlag(self,bCanSend):
		self.canSend = bCanSend
	
	def setDateFormat(self,strFormat):
		self.dateFormat = strFormat
	
	def setLogName(self,strlogName):
		self.logZoneName = strlogName
		
	def GetLogName(self):
		return self.logZoneName
		
	def setLogPostfix(self,strlogfix):
		self.logPostfix = strlogfix
	
	#
	def monitor(self):
		#print 'filename %s' % self.logZonePath
		filename=""
		#had read lines
		count = int(self.readlines)
		#
		waittime = 1.25
		waittimescount = 0
		print 'monitor(self)' + str(os.getpid())
		while True:
			# get date
			thistime = time.strftime(self.dateFormat, time.localtime(time.time()))
			currfilename = self.logZonePath + "/" + self.logZoneName+ str(thistime)+ self.logPostfix
			
			if not os.path.exists(currfilename) :
				print "%s not exist,please check path of config file." % currfilename
				sleeptime = waittime**waittimescount
				#print sleeptime,waittimescount,int(sleeptime)
				time.sleep(int(sleeptime))
				waittimescount += 1
				continue
			else :
				waittimescount = 0
				
			print currfilename
			if filename == "" :
				filename = currfilename
			
			if filename != "" and filename != currfilename:
				count=0
				filename = currfilename
				linecache.clearcache()
			#fileobject = open(filename,'r')
			cache_data = linecache.getlines(filename)
			cachelines = len(cache_data)
			#print "Lines: " + str(cachelines) + " Now:"+str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
			#all_the_text = file_object.read()
			#if count == (cachelines - 1):
			#	continue
			#print "====================:",count
			if count > cachelines:
				count = cachelines
			for lineNum in range(count,cachelines):
				lineline = cache_data[lineNum]
				#print lineline
				if lineline:
					#
					pattern = re.compile(self.regPattern)
					items = re.findall(pattern,lineline)
					if items:
						for item in items:
							print item[0],item[1]
						#send email to notify someone
						print "lineNum:" ,lineNum
						#for itimes in range(2):
						if self.canSend :
							'''
							try :
								self.mailobj.setsubject('Server Error')
								linelinetext = "ServerID: " + self.serverID + "\n"+ lineline + "\nnow :" +str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
								self.mailobj.settext(linelinetext)
								self.mailobj.sendmail()
								self.mailobj.clearContext()
								linelinetext = ""
							except Exception,e:
								print str(e)
							time.sleep(5)
							'''
							linelinetext = ''
							strlineIndex = ''
							lineCount = ''
							strlineIndex = str(self.index)
							#print "strlineIndex:",strlineIndex
							strlineIndex = strlineIndex.zfill(4)
							#print strlineIndex2
							iCounLineNum = lineNum
							lineCount = str(iCounLineNum)
							lineCount = lineCount.zfill(10)
							linelinetext = strlineIndex + lineCount + self.logZoneName +"--"+lineline
							print linelinetext
							self.lock.acquire() #add lock
							self.contentQueue.put(linelinetext)
							lineline = ''
							self.lock.release() #release lock
							
							#write(self.contentQueue,self.lock,lineline)
						#itimes += 1
							#print "times :" + str(itimes)
					else:
						print lineNum, " Not Found"
				else:
					print "now line is null"
				
				
				if lineNum > 0 and ((lineNum+1) % self.linespilte == 0):
					count = lineNum + 1
					break;

				#
				endlinenum = cachelines - 1
				#print str(lineNum)+":::::"+str(endlinenum)
				if int(lineNum) == int(endlinenum):
					count = cachelines
					break
				lineNum += 1	
				
			#except Exception,e: 
				#print str(e) 
				#fileobject.close() 
			time.sleep(5)
			linecache.clearcache()
			
def monitorlogprocess(monitorobjprc):
	monitorobjprc.monitor()
		
if __name__ == "__main__":
	
	ConfFile = "mailConf.ini"
	if not os.path.exists(ConfFile) :
		print "Config file not exist,please check path of config file."
		sys.exit(1)
		
	# get configuration infomation
	cfgobj = ReadConf(ConfFile)
	if not cfgobj.checkSection():
		print "check cfg fialed,please check ini"
		sys.exit(1)
	else :
		print "check ini config file success"
		#sys.exit(1)
		
	#get mail service providers number
	InfoSize = cfgobj.getInt(g_strGlobal,g_strInfoSize)
	ServerMonitor = cfgobj.getInt(g_strGlobal,g_strMonSize)
	list_mailobj = []
	list_indexlinenum = []
	for i in range(InfoSize):
		Username = cfgobj.get(g_strUserInfo%i,g_UsrName)
		Pwd = cfgobj.get(g_strUserInfo%i,g_strPwd)
		Stmp = cfgobj.get(g_strUserInfo%i,g_strStmp)
		
		From = cfgobj.get(g_strMailinfo%i,g_strFrom)
		To = cfgobj.get(g_strMailinfo%i,g_strTo)
		Encoding = cfgobj.get(g_strMailinfo%i,g_strEncoding)
		
		ServerID = cfgobj.get(g_strServerinfo%i,g_strServerID)
		
		OnceSendLines = cfgobj.get(g_strServerinfo%i,g_strOnceSendlins)
		
		#init mailobj
		mailobj = MailHelper("This is python obj",Username,Pwd,Stmp,From,To,ServerID,Encoding,OnceSendLines)
		list_mailobj.append(mailobj)
		
	manager = multiprocessing.Manager()
	contentQueue = manager.Queue()
	lock = manager.Lock() #init lock
	p = multiprocessing.Pool(ServerMonitor+1)
	
	for index in range(ServerMonitor):
		LogPath = cfgobj.get(g_strLoginfo%index,g_strLogPath)
		LogName=cfgobj.get(g_strLoginfo%index,g_strLogName)
		DateFormat=cfgobj.get(g_strLoginfo%index,g_strDateFormat)
		LogPostfix =cfgobj.get(g_strLoginfo%index,g_strLogPostfix)
		OnceReadLines = cfgobj.getInt(g_strLoginfo%index,g_strOnceReadlines)
		ReadLines = cfgobj.getInt(g_strLoginfo%index,g_strHasReadlines)
		RegPattern = cfgobj.get(g_strLoginfo%index,g_strRegpattern)
		hasreaddate=cfgobj.get(g_strLoginfo%index,g_strHasReadDate)
		strNow = str(time.strftime(DateFormat,time.localtime(time.time())))
		if strNow != hasreaddate.strip():
			print "data is not the same day"
			ReadLines = 0
		
		list_indexlinenum.append(ReadLines)
		#print "$$$$$$$$$$$$$$",ReadLines
		monitorobj= MonitorLog(index,OnceReadLines,LogPath,contentQueue,lock,ReadLines)
		monitorobj.setDateFormat(DateFormat)
		monitorobj.setLogName(LogName)
		monitorobj.setLogPostfix(LogPostfix)
		monitorobj.setRegPattern(RegPattern)
		monitorobj.setSendMailFlag(1)
		#print str(index) + LogPath + LogName + DateFormat + LogPostfix + str(OnceReadLines)
		p.apply_async(monitorlogprocess,args=(monitorobj,))

	pr = p.apply_async(read,args=(contentQueue,list_mailobj,InfoSize,list_indexlinenum,cfgobj))
	p.close()
	while True:
		time.sleep(9)
		#print "main"
