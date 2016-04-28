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

strPattern='\[(.*)\]\s+<(.*?)>\s+Failed to decode(.*?)'
#logZoneName = "GameZoneServer_"
#logPostfix = ".log"
#dateFormat = '%Y-%m-%d'


#input msg into Queue
def write(q,lock,linetext):
	if linetext:
		lock.acquire() #add lock
		q.put(linetext)
		lock.release() #release lock

#you can define your email strategy with mutiprocess.
#for some reason,some email service providers might forbit your email address,
#so you had to use serval email address.
	
def read(q,list_mailobj,InfoSize):
	iCount = 0
	while True:
		index = iCount % InfoSize
		iGetCount = 0
		strContext = ''
		time.sleep(10)
		MaxSendlines = list_mailobj[index].getSendLines()
		while not q.empty():
			#set read line limited,so that send many lines by one email  (add on 2016/04/28 by liugao)
			lineline = q.get(False)
			if lineline:
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
				except Execption,e:
					print str(e)
				
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
			except Execption,e:
				print str(e)
			
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
	def __init__(self,OnceReadLines,zoneLogPath,contentQueue,lock):
		self.linespilte = OnceReadLines
		self.logZonePath = zoneLogPath
		self.canSend = 0
		self.dateFormat = ''
		self.logZoneName = ''
		self.logPostfix = ''
		self.contentQueue = contentQueue
		self.lock = lock
		
	#send mailor not
	def setSendMailFlag(self,bCanSend):
		self.canSend = bCanSend
	
	def setDateFormat(self,strFormat):
		self.dateFormat = strFormat
	
	def setLogName(self,strlogName):
		self.logZoneName = strlogName
		
	def setLogPostfix(self,strlogfix):
		self.logPostfix = strlogfix
	
	#
	def monitor(self):
		print 'filename %s' % self.logZonePath
		filename=""
		#had read lines
		count = 0
		#
		waittime = 1.25
		waittimescount = 0
		while True:
			# get date
			thistime = time.strftime(self.dateFormat, time.localtime(time.time()))
			currfilename = self.logZonePath + "\\" + self.logZoneName +"_"+ str(thistime)+ self.logPostfix
			
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
			if filename != currfilename:
				count=0
				filename = currfilename
				linecache.clearcache()
			#fileobject = open(filename,'r')
			cache_data = linecache.getlines(filename)
			cachelines = len(cache_data)
			print "Lines: " + str(cachelines) + " Now:"+str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
			currLineNumber = 0
			#try: 
			if currLineNumber >= cachelines :
				continue
			#all_the_text = file_object.read()
			for lineNum in range(count,cachelines):
				lineline = cache_data[lineNum]
				#print lineline
				if lineline:
					#
					pattern = re.compile(strPattern)
					items = re.findall(pattern,lineline)
					if items:
						for item in items:
							print item[0],item[1]
						#send email to notify someone
						print "lineNum:" + str(lineNum)
						for itimes in range(5):
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
								write(self.contentQueue,self.lock,lineline)
							itimes += 1
							#print "times :" + str(itimes)
					else:
						print str(lineNum) + " :Not Found"
				else:
					print "now line is null"
				lineNum += 1
				if lineNum % self.linespilte == 0:
					count = lineNum
					break;
					
				#
				endlinenum = cachelines - 1
				#print str(lineNum)+":::::"+str(endlinenum)
				if lineNum == endlinenum:
					count = cachelines
			#except Exception,e: 
				#print str(e) 
				#fileobject.close() 
			time.sleep(5)
			linecache.clearcache()
		
if __name__ == "__main__":
	
	ConfFile = "mailConf.ini"
	if not os.path.exists(ConfFile) :
		print "Config file not exist,please check path of config file."
		sys.exit(1)
		
	# get configuration infomation
	cfgobj = ReadConf(ConfFile)
	#get mail service providers number
	InfoSize = cfgobj.getInt('Global','InfoSize')
	list_mailobj = []
	
	for i in range(InfoSize):
		Username = cfgobj.get('UserInfo_%d'%i,'Username')
		Pwd = cfgobj.get('UserInfo_%d'%i,'Password')
		Stmp = cfgobj.get('UserInfo_%d'%i,'MailStmp')
		
		From = cfgobj.get('MailInfo_%d'%i,'From')
		To = cfgobj.get('MailInfo_%d'%i,'To')
		Encoding = cfgobj.get('MailInfo_%d'%i,'Encoding')
		
		ServerID = cfgobj.get('ServerInfo_%d'%i,'ServerID')
		OnceReadLines = cfgobj.getInt('ServerInfo_%d'%i,'OnceReadLines')
		OnceSendLines = cfgobj.get('ServerInfo_%d'%i,'OnceSendLines')
		ZoneLogPath = cfgobj.get('ServerInfo_%d'%i,'ZoneLogPath')
		
		ZoneLogName=cfgobj.get('logInfo_%d'%i,'ZoneLogName')
		DateFormat=cfgobj.get('logInfo_%d'%i,'DateFormat')
		LogPostfix =cfgobj.get('logInfo_%d'%i,'LogPostfix')
		
		#print Username,Pwd,Stmp,From,To,Encoding
		#print ServerID,OnceReadLines,ZoneLogName,DateFormat,LogPostfix
		#print OnceSendLines
		#init mailobj
		mailobj = MailHelper("This is python obj",Username,Pwd,Stmp,From,To,ServerID,Encoding,OnceSendLines)
		list_mailobj.append(mailobj)
		
	#print list_mailobj[0].getSubject(),list_mailobj[0].getUsername(),list_mailobj[0].getPwd()
	#print list_mailobj[1].getSubject(),list_mailobj[1].getUsername(),list_mailobj[1].getPwd()
	#print list_mailobj[2].getSubject(),list_mailobj[2].getUsername(),list_mailobj[2].getPwd()
	
	manager = multiprocessing.Manager()
	contentQueue = manager.Queue()
	lock = manager.Lock() #init lock
	p = Pool(1)
	pr = p.apply_async(read,args=(contentQueue,list_mailobj,InfoSize))
	p.close()
	#p = Process(target=read,args=(contentQueue,list_mailobj,InfoSize))
	#p.start()
	#print "Main PID:"+str(os.getpid())
	
	monitorobj = MonitorLog(OnceReadLines,ZoneLogPath,contentQueue,lock)
	monitorobj.setDateFormat(DateFormat)
	monitorobj.setLogName(ZoneLogName)
	monitorobj.setLogPostfix(LogPostfix)
	monitorobj.setSendMailFlag(1)
	monitorobj.monitor()
	
	
	
	
	
	
