import os.path
import shutil
import time
from enum import Enum
from datetime import datetime
from os.path import getmtime

# Config file definitions
configFileName = 'config.txt'
keywordSource = 'source_folder'
keywordTarget = 'target_folder'

# Command file definitions
commandFileName = '_psc.txt'
dateStringFormat = '%Y/%m/%d, %H:%M:%S'
cmdFileSep = ': '

class CmdFileKeywords(str, Enum):
    FORCE_UPDATE = 'force_update'
    CMD_FILE_TIME = 'file_time'
    ROOT_DIR_TIME = 'dir_time'
    TIMES_MODIFIED = 'times_modified'
    ALBUM_DIRECTORIES = 'album'

# Settings
folderTarget = ""
folderSource = ""
forceUpdateAll = True

def makeEmptyConfigFile():
    print('Creating template config file. Enter configuration data and rerun script.')
    with open(configFileName, 'w') as f:
        f.write(keywordSource + ':\n')
        f.write(keywordTarget + ':\n')
        f.close()

def parseConfigFile():
    global folderSource
    global folderTarget
    cfgFile = open(configFileName, 'r')
    cfgLines = cfgFile.readlines()
    
    for cfgLine in cfgLines:
        cfgPair = cfgLine.split(':', 1)
        lineKeyword = cfgPair[0].strip()
        lineValue = cfgPair[1].strip()
        #print('linekeyword ' + lineKeyword + ', value ' + lineValue)
        if lineKeyword == keywordSource:
            folderSource = lineValue
        elif lineKeyword == keywordTarget:
            folderTarget = lineValue

def verifyConfigParameters():
    if folderSource == "" or not os.path.isdir(folderSource):
        print('Source folder invalid!')
        return False
    if folderTarget == "" or not os.path.isdir(folderTarget):
        print('Target folder invalid!')
        return False
    return True 


logPicIndex = 0
logPicTotal = 0
logLines = ["Header", "", "", "", "", "","","","","","", "Footer"]

def logFileCopy(fileName):
    global logPicIndex
    logLines[0] = 'Copying ' + str(logPicTotal) + ' pictures'
    for i in range(1,10):
        logLines[i] = logLines[i+1]
    logLines[10] = fileName
    logPicIndex += 1
    logLines[11] = 'Progress: ' + str(logPicIndex) + '/' + str(logPicTotal)
    for logItem in logLines:
        print(logItem)
    print('\n')

class CmdFile:
    forceUpdate = False
    timeUpdateDir = ""
    timeUpdateCmdFile = ""
    timesModified = 0
    dtFileTime = datetime.now()
    dtDirTime = datetime.now()
    albumDir = ""

    def readFromFile(self, filePath):
        cmdFile = open(filePath, 'r')
        
        for cmdLine in cmdFile.readlines():
            if len(cmdLine.split(':', 1)) > 1:
                lineKeyword = cmdLine.split(':', 1)[0].strip()
                lineValue = cmdLine.split(':', 1)[1].strip()
                #print('kw ' + lineKeyword + ', val ' + lineValue)

                if lineKeyword == CmdFileKeywords.FORCE_UPDATE:
                    if int(lineValue) > 0:
                        self.forceUpdate = True
                    else:
                        self.forceUpdate = False
                # File update time stamp when last updated
                elif lineKeyword == CmdFileKeywords.CMD_FILE_TIME:
                    self.dtFileTime = datetime.strptime(lineValue, dateStringFormat)
                # Root directory time stamp when last updated
                elif lineKeyword == CmdFileKeywords.ROOT_DIR_TIME:
                    self.dtDirTime = datetime.strptime(lineValue, dateStringFormat)
                # The number of times the file has been updated
                elif lineKeyword == CmdFileKeywords.TIMES_MODIFIED:
                    self.timesModified = int(lineValue)
                # The relative location of the album to the server gallery root folder
                elif lineKeyword == CmdFileKeywords.ALBUM_DIRECTORIES:
                    self.albumDir = lineValue
    
    def writeToFile(self, filePath):
        cmdFile = open(filePath, 'w')
        cmdFile.write(CmdFileKeywords.FORCE_UPDATE + cmdFileSep + '0\n')
        cmdFile.write(CmdFileKeywords.CMD_FILE_TIME + cmdFileSep + self.dtFileTime.strftime(dateStringFormat) + '\n')
        cmdFile.write(CmdFileKeywords.ROOT_DIR_TIME + cmdFileSep + self.dtDirTime.strftime(dateStringFormat) + '\n')
        cmdFile.write(CmdFileKeywords.TIMES_MODIFIED + cmdFileSep + str(self.timesModified) + '\n')
        cmdFile.write(CmdFileKeywords.ALBUM_DIRECTORIES + cmdFileSep + self.albumDir + '\n')

    def updateNeeded(self, dtCmdFile, dtRootDir):
        if dtCmdFile != self.dtFileTime or dtRootDir != self.dtDirTime or self.forceUpdate:
            return True
        else:
            return False

def processCommandFile(path):
    print(path)

def processCommandDirectory(path, dummyRun):
    filesFound = 0
    cmdFilePath = path + os.sep + commandFileName
    dt = datetime.fromtimestamp(os.path.getmtime(path)) # Time stamp of the root folder
    dtf = datetime.fromtimestamp(os.path.getmtime(cmdFilePath)) # Time stamp of the config file
    cmdFile = CmdFile()
    cmdFile.readFromFile(cmdFilePath)

    if not cmdFile.updateNeeded(dtf.replace(microsecond=0), dt.replace(microsecond=0)) and not forceUpdateAll:
        return 0
    
    if not dummyRun:
        # Since a file update was needed, update the file data and write it back
        cmdFile.timesModified += 1
        cmdFile.dtFileTime = datetime.now()
        cmdFile.dtDirTime = dt
        cmdFile.writeToFile(cmdFilePath)
        print('File updated: ' + cmdFilePath)

    # Traverse the files in the folder and perform the copy
    for root, dirs, files in os.walk(path):
        for file in files:
            fileExtension = os.path.splitext(file)[1].lower()
            fileToCopy = root + os.sep + file
            if fileExtension == ".jpg":
                filesFound += 1
                if not dummyRun:
                    logFileCopy(fileToCopy)
                    time.sleep(0.06)
                #print('Copying ' + fileToCopy + ' to ')
                #if not dummyRun:
                    #shutil.copy2(fileToCopy, folderTarget)
    print('Total files: ' + str(filesFound) + ' (' + path + ')')

    return filesFound

# Main ---------------------------------------
if not os.path.isfile(configFileName):
    makeEmptyConfigFile()
    exit()

parseConfigFile()

if not verifyConfigParameters():
    print('Invalid config parameters. Exiting...')
    exit()

print('Parsing source directory (' + folderSource + ')...')

totalFileCounter = 0

# Traverse root directory, and list directories as dirs and files as files. Dummy run only
for root, dirs, files in os.walk(folderSource):
    # Check if the current path contains the command file
    cmdPathName = root + os.sep + commandFileName
    if os.path.isfile(cmdPathName):
        totalFileCounter += processCommandDirectory(root, True)
    
print('Dummy run complete: ' + str(totalFileCounter) + ' files found.')

logPicIndex = 0
logPicTotal = totalFileCounter

# Traverse root directory, and list directories as dirs and files as files. Perform copy
for root, dirs, files in os.walk(folderSource):
    # Check if the current path contains the command file
    cmdPathName = root + os.sep + commandFileName
    if os.path.isfile(cmdPathName):
        processCommandDirectory(root, False)
    #path = root.split(os.sep)
    #print((len(path) - 1) * '---', os.path.basename(root))
    #for file in files:
    #    print(len(path) * '---', file)
        