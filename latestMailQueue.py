#!/usr/bin/Python
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
 
import smtplib  
from email.mime.text import MIMEText  
from email.header import Header

strPattern='\[(.*)\]\s+<(.*?)>\s+Failed to decode(.*?)'
logZoneName = "GameZoneServer_"
logPostfix = ".log"
dateFormat = '%Y-%m-%d'


#由于是在主进程中写入队列
def write(q,lock,linetext):
	if linetext:
		lock.acquire() #加上锁
		q.put(linetext)
		lock.release() #释放锁

#单独开一进程，进行发邮件，这里的邮件分发策略可以自己定义。
#普通邮箱，一般连续发送30-40封邮件，邮件服务器就会封IP
#所以，最好切换不同的邮箱服务商，来避免这样的问题。
#
	
def read(q,list_mailobj,InfoSize):
	iCount = 0
	while True:
		index = iCount % InfoSize
		if not q.empty():
			lineline = q.get(False)
			if lineline:
				try:
					list_mailobj[index].setsubject('Server Error')
					linelinetext = "区服ID: " + list_mailobj[index].getSeverID() + "\n"+ lineline + "\nnow :" +str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
					list_mailobj[index].settext(linelinetext)
					list_mailobj[index].sendmail()
					list_mailobj[index].clearContext()
					linelinetext = ''
					lineline = ''
				except Execption,e:
					print str(e)
				time.sleep(10)
			else:
				print 'context is null'
		else:
			time.sleep(10)
			
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
	def __init__(self,Subject,Username,Pwd,Stmp,From,To,ServerID,Encoding):
		self.subject = Subject
		self.username = Username
		self.pwd = Pwd
		self.stmp = Stmp
		self.sender = From
		self.recevier = To
		self.encoding = Encoding
		self.ServerID = ServerID
		
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
		msg = MIMEText(_text=self.text, _charset=self.encoding) #中文需参数‘utf-8’，单字节字符不需要  
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

#支持动态加载文件，策略非常简单，读完内容以后，每隔5秒重新读一次内容，跳过之前读过的行
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
		
	#是否发送邮件flag设置
	def setSendMailFlag(self,bCanSend):
		self.canSend = bCanSend
	
	def setDateFormat(self,strFormat):
		self.dateFormat = strFormat
	
	def setLogName(self,strlogName):
		self.logZoneName = strlogName
		
	def setLogPostfix(self,strlogfix):
		self.logPostfix = strlogfix
	
	#分析log文件
	def monitor(self):
		print 'filename %s' % self.logZonePath
		filename=""
		#已经匹配的行数
		count = 0
		#指数等待
		waittime = 1.25
		waittimescount = 0
		while True:
			# 当前时间,获取当前系统时间
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
				# 判断内容是否为空
				if lineline:
					#分析行内容

					#正则表达式分析行记录
					pattern = re.compile(strPattern) #re.S表示多行匹配,此不需要
					items = re.findall(pattern,lineline)
					if items:
						for item in items:
							print item[0],item[1]
						#发邮件通知
						print "lineNum:" + str(lineNum)
						for itimes in range(5):
							if self.canSend :
								'''
								try :
									self.mailobj.setsubject('Server Error')
									linelinetext = "区服ID: " + self.serverID + "\n"+ lineline + "\nnow :" +str(time.strftime("%Y-%m-%d %H:%M:%S",time.localtime(time.time())))
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
							print "times :" + str(itimes)
					else:
						print str(lineNum) + " :Not Found"
				else:
					print "now line is null"
				#自主循环
				lineNum += 1
				#一次性读取行数
				if lineNum % self.linespilte == 0:
					count = lineNum
					break;
					
				#读到结尾
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
	#读取配置文件，邮箱用户名，密码等内容
	ConfFile = "mailConf.ini"
	if not os.path.exists(ConfFile) :
		print "Config file not exist,please check path of config file."
		sys.exit(1)
		
	#读取账号信息
	cfgobj = ReadConf(ConfFile)
	#读取邮箱服务商的个数
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
		ZoneLogPath = cfgobj.get('ServerInfo_%d'%i,'ZoneLogPath')
		
		ZoneLogName=cfgobj.get('logInfo_%d'%i,'ZoneLogName')
		DateFormat=cfgobj.get('logInfo_%d'%i,'DateFormat')
		LogPostfix =cfgobj.get('logInfo_%d'%i,'LogPostfix')
		
		#print Username,Pwd,Stmp,From,To,Encoding
		#print ServerID,OnceReadLines,ZoneLogName,DateFormat,LogPostfix
		#发送邮件
		mailobj = MailHelper("This is python obj",Username,Pwd,Stmp,From,To,ServerID,Encoding)
		list_mailobj.append(mailobj)
		
	#print list_mailobj[0].getSubject(),list_mailobj[0].getUsername(),list_mailobj[0].getPwd()
	#print list_mailobj[1].getSubject(),list_mailobj[1].getUsername(),list_mailobj[1].getPwd()
	#print list_mailobj[2].getSubject(),list_mailobj[2].getUsername(),list_mailobj[2].getPwd()
	
	manager = multiprocessing.Manager()
	contentQueue = manager.Queue()
	lock = manager.Lock() #初始化一把锁
	p = Pool(1)
	pr = p.apply_async(read,args=(contentQueue,list_mailobj,InfoSize))
	p.close()
	
	monitorobj = MonitorLog(OnceReadLines,ZoneLogPath,contentQueue,lock)
	monitorobj.setDateFormat(DateFormat)
	monitorobj.setLogName(ZoneLogName)
	monitorobj.setLogPostfix(LogPostfix)
	monitorobj.setSendMailFlag(1)
	monitorobj.monitor()
	
	
	
	
	