import platform
import zipfile
import os
import requests
#############################################################################
#############################################################################

def getLatestReleaseInfo(repoOwner, repoName):

    url = 'https://api.github.com/repos/{}/{}/releases/latest'.\
        format(repoOwner,repoName)

    response = requests.get( url, timeout = 5 )
    if response.status_code == 200:
        latestRelease = response.json()
        #return None, None # For test.
        return latestRelease['tag_name'], latestRelease['html_url']
    return None, None
#############################################################################

def parseReleaseInfo(releaseInfo):
    latestTag  = releaseInfo[0]
    releaseUrl = releaseInfo[1]
    if latestTag:
        #zipUrl = None # For test.
        zipUrl = releaseUrl.replace('releases/tag','archive/refs/tags')+'.zip'
    else:
        zipUrl = None
    return latestTag,releaseUrl,zipUrl
#############################################################################

def getPaths():
    osName     = platform.system()
    if osName == 'Windows':
        dwnldToPath  = 'C:/01-home/temp/' # pylint: disable=C0103
        unzipToPath  = 'C:/01-home/temp/' # pylint: disable=C0103
    elif osName == 'Linux':
        dwnldToPath  = os.getcwd() + '/'
        unzipToPath  = os.getcwd() + '/'
    else:
        dwnldToPath  = None
        unzipToPath  = None
    #return None, None # For test.
    return dwnldToPath, unzipToPath
#############################################################################

def downloadZip( dnldToPath, zipFileUrl ):
    fName = zipFileUrl.split('/')[-1]
    fullyQualifiedFname = dnldToPath + fName
    response = requests.get( zipFileUrl, timeout = 5 )
    status = 'FAIL'
    if response.status_code == 200:
        with open(fullyQualifiedFname,'wb') as outFile:
            outFile.write(response.content)
        status = 'SUCCESS'
    #return 'FAIL', fullyQualifiedFname # For test.
    return status, fullyQualifiedFname
#############################################################################

def unzipFileTo(unzipToPath, fullyQualifiedFname):
    rspStr = ''
    # Unzip directly into the specified directory.
    with zipfile.ZipFile(fullyQualifiedFname, 'r') as f:
        # Get the name of the top-level folder in the zip
        topLevelFolder = f.namelist()[0].split('/')[0]
        for member in f.infolist():
            # Remove the top-level folder from the path
            memberPath = member.filename
            if memberPath.startswith(topLevelFolder + '/'):
                relativePath = memberPath[len(topLevelFolder)+1:]
            else:
                relativePath = memberPath
            if relativePath:  # skip the top-level folder itself
                targetPath = os.path.join(unzipToPath, relativePath)
                if member.is_dir():
                    os.makedirs(targetPath, exist_ok=True)
                else:
                    os.makedirs(os.path.dirname(targetPath), exist_ok=True)
                    if targetPath.split('/')[-1] == 'cfg.cfg':
                        rspStr += '     Skipping {}\n'.format(targetPath)
                    else:
                        with open(targetPath, 'wb') as outfile, f.open(member) as source:
                            rspStr += '     Writing  {}\n'.format(targetPath)
                            outfile.write(source.read())
    return rspStr
#############################################################################

def compareVerNums( swVerLst, repoVerLst ):

    # 0: equal. 1: SW Bigger. 2: Repo Bigger. 3: ERROR.

    if len(swVerLst) != 3 or len(repoVerLst) != 3:
        rtnVal = 3

    elif swVerLst == repoVerLst:      rtnVal = 0

    elif swVerLst[0] > repoVerLst[0]: rtnVal = 1
    elif swVerLst[0] < repoVerLst[0]: rtnVal = 2

    # swVerLst[0] == repoVerLst[0]:
    elif swVerLst[1] > repoVerLst[1]: rtnVal = 1
    elif swVerLst[1] < repoVerLst[1]: rtnVal = 2

    # swVerLst[1] == repoVerLst[1]:
    elif swVerLst[2] > repoVerLst[2]: rtnVal = 1
    elif swVerLst[2] < repoVerLst[2]: rtnVal = 2

    else:                             rtnVal = 3

    return rtnVal # Should never get here,
#############################################################################

def parseVersionNumbers(inVerStrLst):

    verStr    = inVerStrLst[0]
    verLines  = verStr.split('\n')
    appVerStr = verLines[0]
    srvVerStr = verLines[1]

    appVerSplit    = appVerStr.split('=')
    #appVerName     = appVerSplit[0]
    appVerNum      = appVerSplit[1].split(' - ')[0]
    #appVerDt       = appVerSplit[1].split(' - ')[1]
    appV           = [ x.strip() for x in appVerNum.split('.') ]
    appV[0]        = appV[0][1:]
    outAppVerAsIntLst = [int(x) for x in appV]

    srvVerSplit    = srvVerStr.split('=')
    #srvVerName     = srvVerSplit[0]
    srvVerNum      = srvVerSplit[1].split(' - ')[0]
    #srvVerDt       = srvVerSplit[1].split(' - ')[1]
    srvV           = [ x.strip() for x in srvVerNum.split('.') ]
    srvV[0]        = srvV[0][1:]
    outSrvVerAsIntLst = [int(x) for x in srvV]

    #print(' Input Ver String {}'.format( inVerStrLst       ))
    #print(' App Ver as list: {}'.format( outAppVerAsIntLst ))
    #print(' Srv Ver as list: {}'.format( outSrvVerAsIntLst ))
    return outAppVerAsIntLst,outSrvVerAsIntLst
#############################################################################

def updateSw(prmLst):

    verStrLst = prmLst[0]
    repoName  = prmLst[1]
    rspStr = ''

    appVerAsIntLst,srvVerAsIntLst = parseVersionNumbers(verStrLst)

    dwnldToPath,unzipToPath = getPaths()
    if dwnldToPath is None or unzipToPath is None:
        return ['\n FATAL ERROR. dwnld2Path,unzip2Path={},{}\n'.\
                format(dwnldToPath,unzipToPath)]

    rspStr += '\n dwnld2Path,unzip2Path={},{}\n'.format(dwnldToPath,unzipToPath)

    mnRepoOwner = 'sgarrow'
    mnRepoNames = [ repoName, 'sharedClientServerCode']
    localVers   = [  appVerAsIntLst, srvVerAsIntLst]

    for ii, mnRepoName in enumerate(mnRepoNames):

        localVer = localVers[ii]

        releaseInfo = getLatestReleaseInfo(mnRepoOwner,mnRepoName)
        rspStr += '\n Release Info {}  = {}\n'.format(ii,releaseInfo)

        tag,url,zipUrl = parseReleaseInfo(releaseInfo)

        if tag is None or url is None:
            rspStr +=  '   Failed to get the latest release information from {}.\n'.\
                 format( 'github.com/' + mnRepoOwner + '/' + mnRepoName )
            continue
        if zipUrl is None:
            rspStr +=  '   Failed to get url of zip file ({}).\n'.format( zipUrl )
            continue

        repoVerAsLst    = [ x.strip() for x in tag.split('.') ]
        repoVerAsLst[0] = repoVerAsLst[0][1:]
        repoVerAsIntLst = [int(x) for x in repoVerAsLst]

        rspStr += '   Parsed Release Info:'
        rspStr += '     tag    = {}\n'.format( tag    )
        rspStr += '     url    = {}\n'.format( url    )
        rspStr += '     zipUrl = {}\n'.format( zipUrl )
        rspStr += '     repo  SW Ver = {}\n'.format( repoVerAsIntLst )
        rspStr += '     local SW Ver = {}\n'.format( localVer        )

        # 0: equal. 1: SW Bigger. 2: Repo Bigger
        rsp = compareVerNums( localVer, repoVerAsIntLst )
        myStrLst = [ 'same  as', 'older than', 'newer than', '??? than' ]
        rspStr += '   Repo ver is {} running ver.'.format(myStrLst[rsp])
        if rsp == 2:
            rspStr += ' Beginning update.\n'
        else:
            rspStr += ' No update available.\n'
            continue

        sts, fullQualifiedFname = downloadZip(dwnldToPath,zipUrl)
        if sts == 'FAIL':
            rspStr += '   Failed to download {} to {}\n'.\
                format(zipUrl.split('/')[-1],dwnldToPath)
            continue
        rspStr += '   Successfully downloaded {} to {}\n'.\
            format(zipUrl.split('/')[-1],dwnldToPath)

        if sts == 'SUCCESS':
            rspStr += unzipFileTo( unzipToPath, fullQualifiedFname )
            rspStr += '   Successfully extracted {} into {}\n'.\
                format(fullQualifiedFname,unzipToPath)

    return [rspStr]
#############################################################################

if __name__ == '__main__':

    # Can be run stand-alone on command-line on either Windows or Linux,
    # or called my cmdVectors via client on Linux.

    VER = [' appVer =  v1.6.20 - 10-Dec-2025 \n serVer =  v1.7.0 - 10-Dec-2025']
    mnRspStr = updateSw(VER)
    print(mnRspStr[0])
