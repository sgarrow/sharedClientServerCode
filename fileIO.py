import re
import sys
import datetime        as dt
#############################################################################

# Version number of the shared files.
# Calling it the version of the "server".
# As opposed to the version number of the "app" which is in cmdVectors.py
VER = ' v1.7.24 - 09-Feb-2026'

def readFileWrk(parmLst, inFile):
    usage = ' Usage rlf [ numLines [start ["matchStr"]] ].'

    # Get total Lines in file.
    try:
        with open( inFile, 'r',encoding='utf-8') as f:
            numLinesInFile = sum(1 for line in f)
    except FileNotFoundError:
        return ' Could not open file {} for reading'.format(inFile)

    # Get/Calc number of lines to return (parmLst[0]).
    try:
        numLinesToRtnA = int(parmLst[0])
    except ValueError:
        return ' Invalid number of lines to read.\n' + usage

    numLinesToRtn = min( numLinesToRtnA, numLinesInFile )
    numLinesToRtn = max( numLinesToRtn,  1 ) # Don't allow reading 0 lines.

    # Get/Calc startIdx (parmLst[1]).
    if len(parmLst) > 1:
        try:
            startIdx = max(int(parmLst[1]),0)
        except ValueError:
            return ' Invalid startIdx.\n' + usage

        if startIdx > numLinesInFile:
            startIdx = max(numLinesInFile - numLinesToRtn, 0)
    else:
        startIdx = max(numLinesInFile - numLinesToRtn, 0)

    # Calc endIdx.
    endIdx = max(startIdx + numLinesToRtn - 1, 0)
    endIdx = min(endIdx, numLinesInFile-1)

    # Build matchStr.
    numDoubleQuote = 0
    for el in parmLst[2:]:
        if '"' in el:
            numDoubleQuote += el.count('"')
    matchStrEntered = len(parmLst) > 2

    matchStr = ''
    if matchStrEntered and numDoubleQuote == 2:
        startStr = ' '.join(x for x in parmLst[2:] )
        idxLst = [match.start() for match in re.finditer('"', startStr)]
        matchStr = startStr[idxLst[0]+1:idxLst[1]]

    rspStr  = ' numLinesInFile = {:4}.\n'.format( numLinesInFile )
    rspStr += '  numLinesToRtn = {:4}.\n'.format( numLinesToRtn  )
    rspStr += '       startIdx = {:4}.\n'.format( startIdx       )
    rspStr += '         endIdx = {:4}.\n'.format( endIdx         )
    rspStr += '       matchStr = {}.\n\n'.format( matchStr       )

    with open( inFile, 'r',encoding='utf-8') as f:
        for idx,line in enumerate(f):
            if startIdx <= idx <= endIdx:
                if matchStr != '' and matchStr in line:
                    rspStr += ' {:4} - {}'.format(idx,line)
                elif matchStr == '':
                    rspStr += ' {:4} - {}'.format(idx,line)

    return rspStr
#############################################################################

def clearFileWrk(inFile):
    now = dt.datetime.now()
    cDT    = '{}'.format(now.isoformat( timespec = 'seconds' ))
    with open(inFile, 'w',encoding='utf-8') as f:
        f.write( 'File cleared on {} \n'.format(cDT))
    return ' {} file cleared.'.format(inFile)
#############################################################################

def readFile(parmLst):
    fName = parmLst[0]
    linesToRead = parmLst[1]
    sys.stdout.flush()
    rspStr = readFileWrk(linesToRead, fName)
    return [rspStr]
#############################################################################

def clearFile(parmLst):
    fName = parmLst[0]
    sys.stdout.flush()
    rspStr = clearFileWrk(fName)
    return [rspStr]
#############################################################################

def writeFile(fName, inStr):
    with open(fName, 'a', encoding='utf-8') as f:
        f.write( inStr )
        f.flush()
##############################################################################
