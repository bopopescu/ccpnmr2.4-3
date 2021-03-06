#@PydevCodeAnalysisIgnore
# Trial script for automatic compaction and transmission
# of a CCPN project to an iCing server.

import os, tarfile, time, random, glob
import httplib, mimetypes, mimetools

try:
  import urllib2
except ImportError, err:
  print "* Warning * Cannot import Python module urllib2."
  print " - Please check your SSL libraries."
  print " - Submission to to the iCing server will not work."
  print err

from memops.gui.MessageReporter import showWarning, showYesNo

FORM_ACCESS_KEY = "AccessKey"
FORM_USER_ID = "UserId"
FORM_UPLOAD_FILE = "UploadFile"
FORM_ACTION = "Action"
FORM_ACTION_RUN = "Run"
FORM_ACTION_SAVE = "Save"
FORM_ACTION_STATUS = "Status"
FORM_ACTION_PROJECT_NAME = "ProjectName"
FORM_ACTION_PURGE = "Purge"
FORM_ACTION_LOG = "Log"

FORM_RESIDUES = "Residues"
FORM_ENSEMBLE = "Ensemble"
FORM_VERBOSITY = "Verbosity"

RESPONSE_EXIT_CODE = 'ExitCode'
RESPONSE_SUCCESS = 'Success'
RESPONSE_RESULT = 'Result'
RESPONSE_DONE = 'done'

ALPHANUMERIC = [chr(x) for x in range(48,58)+range(65,91)+range(97,123)]
random.shuffle(ALPHANUMERIC)
    
def testProjectPakageMacro(argServer):

  _packageProject(argServer.getProject())

def ccpnCingSubmitMacro(argServer, url="https://nmr.le.ac.uk/"):
    """CcpNmr Analysis macro to test ending CCPN projects to iCing"""

    project = argServer.getProject()

    if project:
        iCingUrl = os.path.join(url, 'icing/serv/iCingServlet')
    
        credentials, results, tarFileName = iCingSetup(project, url=iCingUrl)
        print credentials
        print results

        if results:
            
            entryId = iCingProjectName(credentials, iCingUrl).get(RESPONSE_RESULT)
            urls = getResultUrls(credentials, entryId, url)
            print "Base URL", urls[0]
            print "Results URL:", urls[1]
            print "Log URL:", urls[2]
            print "Zip URL:", urls[3]
             
            print iCingRun(credentials, iCingUrl)
            
            status = iCingStatus(credentials, iCingUrl)

            print status
            for i in range(100):
              time.sleep(60)
              status2 = iCingStatus(credentials, iCingUrl)
              print status2
              
              if status2 != status:
                break
            
            print "Done"
            #print iCingLog(credentials, url)

            zipFileName = argServer.getFile()
            
            if zipFileName:
              logText = iCingFetch(credentials, url, iCingUrl, zipFileName)
              argServer.showInfo('Results saved to %s' % zipFileName)
              print logText
            else:
              argServer.showInfo('No file name')
            
            print iCingPurge(credentials, url)
            
            
def getResultUrls(credentials, entryId, url="https://nmr.le.ac.uk/"):
  
    userId = credentials[0][1]
    accessKey = credentials[1][1]
 
    resultBaseUrl = os.path.join(url, 'tmp/cing', userId, accessKey)
    resultHtmlUrl = os.path.join(resultBaseUrl, entryId + ".cing", "index.html")
    resultLogUrl = os.path.join(resultBaseUrl, "cingRun.log")
    resultZipUrl = os.path.join(resultBaseUrl, entryId + "_CING_report.zip")

    return resultBaseUrl, resultHtmlUrl, resultLogUrl, resultZipUrl

def getRandomKey(size=6):
    """Get a random alphanumeric string of a given size"""

    n = len(ALPHANUMERIC)-1
    random.seed(time.time()*time.time())

    return ''.join([ALPHANUMERIC[random.randint(0,n)] for x in range(size)])


def iCingSetup(memopsRoot, userId='ccpnAp', doSave=True,
               url="https://nmr.le.ac.uk/icing/icing/serv/iCingServlet"):
    """Function to send a CCPN project (memops root object) to an iCing server.
       Returns credentials used for that job and the server response.
    """
    
    projectTgz = _packageProject(memopsRoot)
    if not projectTgz:
        return
    
    # Access credentials.
    accessKey = getRandomKey()
    credentials = [(FORM_USER_ID, userId), (FORM_ACCESS_KEY, accessKey)]
    
    result = None
    # Send the project
    if doSave:
        data = credentials + [(FORM_ACTION,FORM_ACTION_SAVE),]
        fileObj = open(projectTgz, 'rb')
        files = [( FORM_UPLOAD_FILE, projectTgz, fileObj.read() ),]
        result = sendRequest(url, data, files)
     
    return credentials, result, projectTgz
   
    
def iCingStatus(credentials, url):
    """Check iCing server status associated with given credentials.
    """
     
    data = credentials + [(FORM_ACTION,FORM_ACTION_STATUS),]
    return  sendRequest(url, data, files=None)


def iCingRun(credentials, url):
    """Run an iCing server job associated with given credentials.
    """
     
    data = credentials + [(FORM_ACTION,FORM_ACTION_RUN),]
    return  sendRequest(url, data, files=None)

def iCingResidueSelection(credentials, url, residuesString):
    """Send a residue selection to the iCing server
    """
     
    data = credentials + [(FORM_RESIDUES,residuesString),]
    return  sendRequest(url, data, files=None)
    
def iCingEnsembleSelection(credentials, url, modelsString):
    """Send a residue selection to the iCing server
    """
     
    data = credentials + [(FORM_ENSEMBLE,modelsString),]
    return  sendRequest(url, data, files=None)
  
def iCingLog(credentials, url):
    """Get iCing server log associated with given credentials.
    """
     
    data = credentials + [(FORM_ACTION,FORM_ACTION_LOG),]
    return  sendRequest(url, data, files=None)


def iCingProjectName(credentials, url):
    """Get CCPM project name at iCing server associated with given credentials.
    """
     
    data = credentials + [(FORM_ACTION,FORM_ACTION_PROJECT_NAME),]
    return  sendRequest(url, data, files=None)


def iCingPurge(credentials, url):
    """Purge a job on iCing server associated with given credentials.
    """
     
    data = credentials + [(FORM_ACTION,FORM_ACTION_PURGE),]
    return  sendRequest(url, data, files=None)


def iCingFetch(credentials, url, iCingUrl, zipFileName):
    """Fetch a CCPn project from an  job on iCing server associated with given credentials.
    """
     
    response = iCingProjectName(credentials, iCingUrl)
    if not response:
        msg = 'Fetch not possible'
        showWarning('Warning', msg)
        return
    
    entryId = response.get(RESPONSE_RESULT)
    baseUrl, resultUrl, logUrl, zipUrl = getResultUrls(credentials, entryId, url)
    
    #print "Base URL", baseUrl
    #print "Results URL:", resultUrl
    #print "Log URL:", logUrl
    #print "Zip URL:", zipUrl
    
    response = urlOpen(logUrl)
    if response:
      logText = response.read()
      
    response = urlOpen(zipUrl)
    if response:
      file = open(zipFileName, 'wb')
      file.write(response.read())
      file.close()

    return logText
     
           
def _packageProject(memopsRoot):
    """Create a tar gzipped CCPN project from a MemopsRoot object"""    
    
    from memops.general.Io import saveProject, packageProject
    
    repository = memopsRoot.findFirstRepository(name='userData')
    if not repository:
        return
    
        
    projectPath = repository.url.path
    parentDir, projectDir = os.path.split(projectPath)

    
    writeable = os.access(parentDir, os.W_OK)
    if not writeable:
        msg = 'Directory %s does not have write access required to write temporary file.'
        showWarning('Warning', msg % parentDir)
        return
    
    currentProjName = memopsRoot.name
    newProjName = '__%s' % currentProjName
    newProjDir = os.path.join(parentDir, newProjName)
    
    while os.path.exists(newProjDir):
        msg = 'Filename %s exists. Overwrite?' % newProjDir
        if showYesNo('Query', msg): 
            break
        
        newProjName = '_' + newProjName
        newProjDir = os.path.join(parentDir, newProjName)
    
    try:
      saveProject(memopsRoot, newPath=newProjDir, removeExisting=True, revertToOriginal=True)
    
      packageProject(memopsRoot, filePrefix=newProjDir, userPath=newProjDir)
    finally:
      # reset project name
      # need to use override since name is frozen
      # wb104: 6 Feb 2014: should not need to do below any more because added revertToOriginal and userPath above
      #memopsRoot.override = True
      #memopsRoot.name = currentProjName
      #memopsRoot.override = False
      pass

    return newProjDir + '.tgz'


#########################################################################################
# Initial code from http://www.voidspace.org.uk/python/cgi.shtml#upload                                                #
#########################################################################################

###BOUNDARY = mimetools.choose_boundary()

def encodeForm(fields, files=None, lineSep='\r\n',
               boundary=None):
               ###boundary='-----'+BOUNDARY+'-----'):
    """Function to encode form fields and files so that they can be sent to a URL"""

    if not boundary:
      boundary = boundary = '-----'+mimetools.choose_boundary()+'-----'

    if not files:
        files = []

    lines = []
    if isinstance(fields, dict):
        fields = fields.items()
 
        
    for (key, fileName, value) in files:
        #fileType = mimetypes.guess_type(fileName)[0] or 'application/octet-stream'
        fileType = 'application/octet-stream'
        
        lines.append('--' + boundary)
        lines.append('Content-Disposition: form-data; name="%s"; filename="%s"' % (key, fileName))
        if not fileType.startswith('text'):
            lines.append('Content-Transfer-Encoding: binary')
        lines.append('Content-Type: %s' % fileType)
        #lines.append('Content-Length: %s\r\n' % str(len(value)))
        lines.append('')
        lines.append(value)
        
    for (key, value) in fields:
        lines.append('--' + boundary)
        lines.append('Content-Disposition: form-data; name="%s"' % key)
        lines.append('')
        lines.append(value)
     
    
    lines.append('--' + boundary + '--')
    lines.append('')
    
    bodyData = lineSep.join(lines)
    contentType = 'multipart/form-data; boundary=%s' % boundary 
 
    return contentType, bodyData


def urlOpen(request):

    try:
        response = urllib2.urlopen(request)

    except urllib2.URLError, e:
        if hasattr(e, 'reason'):
            if isinstance(request, urllib2.Request):
              url = request.get_full_url()
            else:
              url = request
              
            msg = 'Connection to server URL %s failed with reason:\n%s' % (url, e.reason)
            
        elif hasattr(e, 'code'):
            msg =    'Server request failed and returned code:\n%s' % e.code 
            
        else:
            msg = 'Server totally barfed with no reason or fail code'
        
        showWarning('Failure', msg)     
        return

    return response


def sendRequest(url, fields, files):
    """Function to send form fields and files to a given URL.
    """

    contentType, bodyData = encodeForm(fields, files)
    
    headerDict = {'User-Agent': 'anonymous',
                  'Content-Type': contentType,
                  'Content-Length': str(len(bodyData))
                  }
        
    request = urllib2.Request(url, bodyData, headerDict)
    response = urlOpen(request)
    
    if not response:
      return
    
    jsonTxt = response.read()
            
    result = _processResponse(jsonTxt)
    if result.get(RESPONSE_EXIT_CODE) != RESPONSE_SUCCESS:
        msg  = 'Request not successful. Action was: %s' % fields
        msg += ' Response was: %s' % jsonTxt
        showWarning('Failure', msg)
        return
    
    return result


def _processResponse(text):
    """Convert the strings the iCingServer sends back into Python
       When Python 2.6 is the CCPn standards this should use the JSON
       libraries.
    """

    text = text[2:-2]
    
    dataDict = {}
    
    for pair in text.split('","'):
      data = pair.split('":"')
    
      if len(data) == 2:
        key , value = data
        dataDict[key] = value
      else:
        print "Trouble",  pair
            
    
    return dataDict

if __name__ == '__main__':

  for i in range(80):
    print getRandomKey()
