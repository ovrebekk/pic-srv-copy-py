import os.path
import shutil
import time
import subprocess
from enum import Enum
from datetime import datetime
from os.path import getmtime
import imageio.v3 as iio
from PIL import Image, ExifTags
import exifread

# Config file definitions
configFileName = 'config.txt'
keywordSource = 'source_folder'
keywordTarget = 'target_folder'
keywordHostMode = 'host_mode'

# Command file definitions
commandFileName = '_psc.txt'
dateStringFormat = '%Y/%m/%d, %H:%M:%S'
dateOnlyFormat = '%Y/%m/%d'
cmdFileSep = ': '
dayPostFix = ['th','st','nd','rd','th','th','th','th','th','th']

class AlbumCategories(str, Enum):
    TRAVEL = 'travel'
    EVENT = 'event'
    HOME = 'home'
    UGLER = 'ugler'
    NORDIC = 'nordic'
    MISC = 'misc'
    INVALID = ''

    def getFolderName(self):
        if self == AlbumCategories.TRAVEL:
            return 'Travel/%Y/'
        elif self == AlbumCategories.EVENT:
            return 'Events/%Y/'
        elif self == AlbumCategories.HOME:
            return 'Home/%Y/'
        elif self == AlbumCategories.NORDIC:
            return 'Nordic/%Y - '
        elif self == AlbumCategories.UGLER:
            return 'Ugler/%Y/'
        elif self == AlbumCategories.MISC:
            return 'Misc/%Y/'
        else:
            return ''

class CmdFileKeywords(str, Enum):
    CATEGORY = 'category'
    ALBUM_NAME = 'album'
    FORCE_UPDATE = 'force_update'
    INCLUDE_VIDEO = 'include_video'
    RATING_TARGET = 'rating_target'
    CMD_FILE_TIME = 'file_time'
    ROOT_DIR_TIME = 'dir_time'
    CREATION_DATE = 'creation_date'
    TIMES_MODIFIED = 'times_modified'
    TARGET_COPY_FOLDER = 'target_copy_folder'

# Settings
folderTarget = ""
folderSource = ""
hostMode = 0
forceUpdateAll = False
includeVideos = True

def makeEmptyConfigFile():
    print('Creating template config file. Enter configuration data and rerun script.')
    with open(configFileName, 'w') as f:
        f.write(keywordSource + ':\n')
        f.write(keywordTarget + ':\n')
        f.close()

def parseConfigFile():
    global folderSource
    global folderTarget
    global hostMode
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
        elif lineKeyword == keywordHostMode:
            hostMode = int(lineValue)

def verifyConfigParameters():
    if folderSource == "" or not os.path.isdir(folderSource):
        print('Source folder invalid: ' + folderSource)
        return False
    if folderTarget == "" or not os.path.isdir(folderTarget):
        print('Target folder invalid: ' + folderTarget)
        return False
    return True 

class CmdFile:
    forceUpdate = False
    includeVideo = 0
    ratingTarget = 0
    timeUpdateDir = ""
    timeUpdateCmdFile = ""
    timesModified = 0
    dtCreationDate = datetime.min
    dtFileTime = datetime.now()
    dtDirTime = datetime.now()
    albumName = ""
    albumNameOrig = ""
    category = AlbumCategories.INVALID
    targetFolderOnLastCopy = ""
    rootFolder = ""
    pictureList = []
    videoList = []
    requirementMet = 0

    def readFromFile(self, filePath):
        cmdFile = open(filePath, 'r')
        
        for cmdLine in cmdFile.readlines():
            if len(cmdLine.split(':', 1)) > 1:
                lineKeyword = cmdLine.split(':', 1)[0].strip()
                lineValue = cmdLine.split(':', 1)[1].strip()
                #print('kw ' + lineKeyword + ', val ' + lineValue)

                if lineKeyword == CmdFileKeywords.CATEGORY:
                    try:
                        AlbumCategories(lineValue)
                    except:
                        self.category = AlbumCategories.INVALID
                    else:
                        self.category = AlbumCategories(lineValue)
                        self.requirementMet += 1
                # The relative location of the album to the server gallery root folder
                elif lineKeyword == CmdFileKeywords.ALBUM_NAME and lineValue != "":
                    self.albumNameOrig = lineValue
                    self.albumName = lineValue.replace(' ','_').replace('æ','ae').replace('ø','oe').replace('å','aa').replace('Æ','Ae').replace('Ø','Oe').replace('Å','Aa')
                    self.requirementMet += 1
                elif lineKeyword == CmdFileKeywords.FORCE_UPDATE:
                    if int(lineValue) > 0:
                        self.forceUpdate = True
                    else:
                        self.forceUpdate = False
                # Whether or not to include videos
                elif lineKeyword == CmdFileKeywords.INCLUDE_VIDEO:
                    self.includeVideo = int(lineValue)
                # The rating threshold required for including an image
                elif lineKeyword == CmdFileKeywords.RATING_TARGET:
                    self.ratingTarget = int(lineValue)
                # File update time stamp when last updated
                elif lineKeyword == CmdFileKeywords.CMD_FILE_TIME:
                    try:
                        self.dtFileTime = datetime.strptime(lineValue, dateStringFormat)
                    except:
                        self.dtFileTime = datetime.min
                # Root directory time stamp when last updated
                elif lineKeyword == CmdFileKeywords.ROOT_DIR_TIME:
                    try:
                        self.dtDirTime = datetime.strptime(lineValue, dateStringFormat)
                    except:
                        self.dtDirTime = datetime.min
                # Creation date of the images in the folder
                elif lineKeyword == CmdFileKeywords.CREATION_DATE:
                    try:
                        self.dtCreationDate = datetime.strptime(lineValue, dateOnlyFormat)
                    except:
                        self.dtCreationDate = datetime.min
                # The number of times the file has been updated
                elif lineKeyword == CmdFileKeywords.TIMES_MODIFIED:
                    self.timesModified = int(lineValue)
                elif lineKeyword == CmdFileKeywords.TARGET_COPY_FOLDER:
                    self.targetFolderOnLastCopy = lineValue

    
    def writeToFile(self, filePath):
        outFile = open(filePath, 'w')
        outFile.write('------ User parameters ------\n\n')
        outFile.write(CmdFileKeywords.CATEGORY + cmdFileSep + self.category + '\n')
        outFile.write(CmdFileKeywords.ALBUM_NAME + cmdFileSep + self.albumNameOrig + '\n')
        outFile.write(CmdFileKeywords.FORCE_UPDATE + cmdFileSep + '0\n')
        outFile.write(CmdFileKeywords.INCLUDE_VIDEO + cmdFileSep + str(self.includeVideo) + '\n')
        outFile.write(CmdFileKeywords.RATING_TARGET + cmdFileSep + str(self.ratingTarget) + '\n')
        
        outFile.write('\n------ Generated parameters ------\n\n')
        outFile.write(CmdFileKeywords.CMD_FILE_TIME + cmdFileSep + datetime.now().strftime(dateStringFormat) + '\n')
        outFile.write(CmdFileKeywords.ROOT_DIR_TIME + cmdFileSep + self.dtDirTime.strftime(dateStringFormat) + '\n')
        outFile.write(CmdFileKeywords.CREATION_DATE + cmdFileSep + self.dtCreationDate.strftime(dateOnlyFormat) + '\n')
        outFile.write(CmdFileKeywords.TIMES_MODIFIED + cmdFileSep + str(self.timesModified) + '\n')
        if self.targetFolderOnLastCopy != "":
            outFile.write(CmdFileKeywords.TARGET_COPY_FOLDER + cmdFileSep + self.targetFolderOnLastCopy + '\n')

    def getDayString(self):
        #dayString = datetime.strftime(self.dtCreationDate, "%a_")
        dayString = str(self.dtCreationDate.day)
        if self.dtCreationDate.day >= 10 and self.dtCreationDate.day <= 20:
            dayString += dayPostFix[9]
        else:
            dayString += dayPostFix[self.dtCreationDate.day % 10]
        dayString += datetime.strftime(self.dtCreationDate, "_%b")
        return dayString

    def updateNeeded(self, dtCmdFile, dtRootDir):
        dtFileTimeDiffSeconds = (dtCmdFile - self.dtFileTime).total_seconds() # Allow some seconds of difference, since network write operations are slow
        if abs(dtFileTimeDiffSeconds) > 2 or dtRootDir != self.dtDirTime:
            #print('Update needed file time ' + dtCmdFile.strftime("%m/%d/%Y, %H:%M:%S") + ' ' + self.dtFileTime.strftime("%m/%d/%Y, %H:%M:%S"))
            #print('Dir time ' + dtRootDir.strftime("%m/%d/%Y, %H:%M:%S") + ' ' + self.dtDirTime.strftime("%m/%d/%Y, %H:%M:%S"))
            return True
        if self.forceUpdate:
            #print('Update needed forceupdate')
            return True
        else:
            return False
    
    def contentValid(self):
        if self.requirementMet == 2 and self.category != AlbumCategories.INVALID and self.dtCreationDate != datetime.min:
            return True
        else: 
            return False

def processCommandFile(path):
    print(path)

def getJpgFileRating(jpgFile):
    IMAGE_RATING_TAG = "Image Rating"

    # Open image with ExifMode to collect EXIF data
    exif_tags = open(jpgFile, 'rb')
    tags = exifread.process_file(exif_tags)

    rating = 0
    # Try to read the image rating tag first
    if IMAGE_RATING_TAG in tags.keys():
        rating = int(tags.get(IMAGE_RATING_TAG).values[0])
    # If this tag can not be found, look for the rating in the xmp data
    else:
        with open(jpgFile, "rb") as fin:
            img = fin.read()
            imgAsString = str(img)
            xmp_start = imgAsString.find('xmp:Rating=')
            rating_str = imgAsString[xmp_start+12:xmp_start+13]
            if rating_str.isdigit():
                rating = int(rating_str)

    return rating

def checkCommandDirectory(path):
    cmdFilePath = path + os.sep + commandFileName
    dt = datetime.fromtimestamp(os.path.getmtime(path)) # Time stamp of the root folder
    dtf = datetime.fromtimestamp(os.path.getmtime(cmdFilePath)) # Time stamp of the config file
    cmdFile = CmdFile()
    cmdFile.readFromFile(cmdFilePath)
    cmdFile.pictureList = []
    cmdFile.videoList = []
    if cmdFile.updateNeeded(dtf.replace(microsecond=0), dt.replace(microsecond=0)) or forceUpdateAll:
        for root, dirs, files in os.walk(path):
            if cmdFile.includeVideo:
                for file in files:
                    fileExtension = os.path.splitext(file)[1].lower()
                    if fileExtension == ".mp4":
                        cmdFile.videoList.append(root + os.sep + file)   
            if root == path: # TODO: Add functionality to also go through subfolders
                # Count all the JPG files
                for file in files:
                    fileExtension = os.path.splitext(file)[1].lower()
                    if fileExtension == ".jpg":
                        if cmdFile.ratingTarget == 0 or getJpgFileRating(root + os.sep + file) >= cmdFile.ratingTarget: 
                            cmdFile.pictureList.append(root + os.sep + file)
        cmdFile.rootFolder = path
        return cmdFile
    else:
        return None

def processCommandDirectory(cFile):
    filesFound = 0
    cmdFilePath = cFile.rootFolder + os.sep + commandFileName
    dt = datetime.fromtimestamp(os.path.getmtime(cFile.rootFolder)) # Time stamp of the root folder
    dtf = datetime.fromtimestamp(os.path.getmtime(cmdFilePath)) # Time stamp of the config file
    
    # Since a file update was needed, update the file data and write it back
    cFile.timesModified += 1
    cFile.dtDirTime = dt
    if cFile.dtCreationDate == datetime.min:
        # Try to read the creation date of this image folder from the folder name
        splitPath = cFile.rootFolder.split(os.sep)
        topFolder = splitPath[len(splitPath) - 1]
        try:
            cFile.dtCreationDate = datetime.strptime(topFolder[:8], "%y_%m_%d")
        except:
            print('Failed to convert folder name to date!')
    cFile.writeToFile(cmdFilePath)
    print('File updated: ' + cmdFilePath)

    if cFile.contentValid():
        # Traverse the files in the folder and perform the copy
        for root, dirs, files in os.walk(cFile.rootFolder):
            if root == cFile.rootFolder: # TODO: Add functionality to also go through subfolders
                copyToPath = cFile.category.getFolderName() + cFile.albumName

                # Search for datetime markers in the folder names and replace accordingly
                pathPieces = copyToPath.split('/')
                for i in range(0,len(pathPieces)):
                    if pathPieces[i].find('%DAY') >= 0:
                        pathPieces[i] = pathPieces[i].replace('%DAY', cFile.getDayString())
                    if pathPieces[i].find('%') >= 0:
                        try:
                            pathPieces[i] = datetime.strftime(cFile.dtCreationDate, pathPieces[i])
                        except:
                            print('Error converting folder name to datetime string')
                
                copyToPath = folderTarget + os.sep + os.sep.join(pathPieces) + os.sep
                print('Copypath: ' + copyToPath)

                # Store the relative target folder to the command file for future reference
                if cFile.targetFolderOnLastCopy != os.sep.join(pathPieces):
                    cFile.targetFolderOnLastCopy = os.sep.join(pathPieces)
                    cFile.writeToFile(cmdFilePath)
                
                # Check if the target folder exists, create it otherwise
                if os.path.exists(copyToPath):
                    print('Folder exists! TODO: Delete existing images?')
                else:
                    os.makedirs(copyToPath)
                # Copy all the correct files to the selected target directory
                for file in cFile.pictureList:
                    fileExtension = os.path.splitext(file)[1].lower()
                    fileToCopy = file
                    if os.path.isfile(copyToPath + os.sep + file):
                        print('File ' + fileToCopy + ' exists. Skipping..')
                    else:
                        fileSize = os.path.getsize(fileToCopy)
                        startTime = time.time()
                        shutil.copy2(fileToCopy, copyToPath)
                        elapsedTime = time.time() - startTime
                        speedMbps = 0
                        if elapsedTime > 0:
                            speedMbps = float(fileSize) * 8 / 1024 / 1024 / elapsedTime
                        print(fileToCopy + ' copied in ' + str(int(elapsedTime*1000)) + ' ms, speed ' + str(int(speedMbps)) + ' Mbps')
            
                # After all the images have been moved, convert and move all video files
                if includeVideos and cFile.includeVideo:
                    for vidFile in cFile.videoList:
                        targetVid = copyToPath + os.path.splitext(os.path.split(vidFile)[1])[0] + '_r.mp4'
                        if os.path.isfile(targetVid):
                            print('Video already exists. Skipping: ' + targetVid)
                        else:
                            print('Converting video: ' + vidFile)
                            subprocess.run(["ffmpeg", "-i",vidFile,"-movflags","use_metadata_tags","-map_metadata","0","-c:v", "libx264", "-preset","slow","-crf","20","-filter:v","scale=1920:-1","-c:a","copy",targetVid])

            else:
                for file in files:
                    fileExtension = os.path.splitext(file)[1].lower()
                    fileToCopy = root + os.sep + file
                    if fileExtension == ".jpg":
                        filesFound += 1
        
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
totalVideoCounter = 0
cmdFileToProcessList = []

# Traverse root directory, and list directories as dirs and files as files. Dummy run only
for root, dirs, files in os.walk(folderSource):
    # Check if the current path contains the command file
    cmdPathName = root + os.sep + commandFileName
    if os.path.isfile(cmdPathName):
        cmdFile = checkCommandDirectory(root)
        if cmdFile != None:
            totalFileCounter += len(cmdFile.pictureList)
            totalVideoCounter += len(cmdFile.videoList)
            cmdFileToProcessList.append(cmdFile)
            print('Found folder: ' + cmdFile.rootFolder)
            print('Pictures: ' + str(len(cmdFile.pictureList)) + ', Videos: ' + str(len(cmdFile.videoList)))
    
print('Folder search complete. Found ' + str(totalFileCounter) + ' new pictures and ' + str(totalVideoCounter) + ' new videos.')

if hostMode == 1:
    print('Host mode enabled. Skipping file copy operation')
    exit()

if not includeVideos:
    print('Videos will be omitted')

input("Press Enter to continue...")

# Traverse list of registered command files and execute them one by one
for cmdFile in cmdFileToProcessList:
    processCommandDirectory(cmdFile)

print("Script finished!")
        