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
dateStringFormat = '%d/%m/%Y, %H:%M:%S'

class CmdFileKeywords(str, Enum):
    FORCE_UPDATE = 'force_update'
    CMD_FILE_TIME = 'file_time'
    DIR_FILE_TIME = 'dir_time'

folderTarget = ""
folderSource = ""

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

class CmdFile:
    forceUpdate = False

    def readFromFile(self, filePath):
        cmdFile = open(filePath, 'r')
        
        for cmdLine in cmdFile.readlines():
            if len(cmdLine.split(':', 1)) > 1:
                lineKeyword = cmdLine.split(':', 1)[0].strip()
                lineValue = cmdLine.split(':', 1)[1].strip()
                print('kw ' + lineKeyword + ', val ' + lineValue)

def processCommandFile(path):
    print(path)

def processCommandDirectory(path, dummyRun):
    fileCounter = 0
    cmdFilePath = path + os.sep + commandFileName
    dt = datetime.fromtimestamp(os.path.getmtime(path))
    dtf = datetime.fromtimestamp(os.path.getmtime(cmdFilePath))
    cmdFile = CmdFile()
    cmdFile.readFromFile(cmdFilePath)
    for root, dirs, files in os.walk(path):
        for file in files:
            fileExtension = os.path.splitext(file)[1].lower()
            fileToCopy = root + os.sep + file
            if fileExtension == ".jpg":
                fileCounter += 1
                #print('Copying ' + file + ' to ')
                #shutil.copy2(fileToCopy, folderTarget)
    print('Total files: ' + str(fileCounter) + ' (' + path + ')')

# Main ---------------------------------------
if not os.path.isfile(configFileName):
    makeEmptyConfigFile()
    exit()

parseConfigFile()

if not verifyConfigParameters():
    print('Invalid config parameters. Exiting...')
    exit()

print('Parsing source directory (' + folderSource + ')...')

# traverse root directory, and list directories as dirs and files as files
for root, dirs, files in os.walk(folderSource):
    # Check if the current path contains the command file
    cmdPathName = root + os.sep + commandFileName
    if os.path.isfile(cmdPathName):
        processCommandDirectory(root, True)
    #path = root.split(os.sep)
    #print((len(path) - 1) * '---', os.path.basename(root))
    #for file in files:
    #    print(len(path) * '---', file)