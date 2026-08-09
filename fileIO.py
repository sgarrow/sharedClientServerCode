import re
import sys
import datetime        as dt
#############################################################################

# Version number of the shared files.
# Calling it the version of the "server".
# As opposed to the version number of the "app" which is in cmdVectors.py
VER = 'v1.8.10 - 08-Aug-2026'

def readFileWrk(parmLst, inFile):

    usage = \
 '''
Example parameters:

 <NONE>    - return 5 lines starting from - 5th line from bottom.
 3         - return 3 lines starting from - 3rd line from bottom.
 3 4       - return 3 lines starting from - line 4 (0 is 1st line).
 
 "match"   - return all lines with    "match" in it.
 3 "match" - return last 3 lines with "match" in it.
 "match", 3 - return last 3 lines with "match" in it.

 Note: '"match this"' (two words) not supported (too many parms).

'''

    print(parmLst) # All parameters get passed in as strings.
    numParms = len(parmLst)

    # Get total Lines in file.
    try:
        with open( inFile, 'r',encoding='utf-8') as f:
            numLinesInFile = sum(1 for line in f)
    except FileNotFoundError:
        return ' Could not open file {} for reading'.format(inFile)
    ###########################

    # Verify correct number of parameters
    if not 0 < numParms < 3:
        return ' Incorrect number of parameters.' + usage
    ###########################

    # See if there is (at most) 1 parameter of the form '"match"'
    # Note: '"match this"' (two words) not supported.
    matchStr    = ''
    numMatchStr = 0
    for idx,el in enumerate(parmLst):
        if el == '""':
            return ' Empty match string not supported.' + usage
        if el.startswith('"') and el.endswith('"'):
            matchSrtAtIdx = idx
            matchStr      = el[1:-1]
            numMatchStr  += 1
        if numMatchStr > 1:
            return ' Multiple match strings not supported.' + usage
    ###########################

    # If match str provided, get number of matches to return.
    # The start/end file index is hardcoded to 0, and nm lines in file.
    numLinesToRtn   = 0 # Loop control when no match string supplied
    numMatchesToRtn = 0 # Loop control when  q match string supplied 
    if numMatchStr:
        if numParms > 1:
            idxToCastToInt = 0 if matchSrtAtIdx == 1 else 1
            try:
                numMatchesToRtn = int(parmLst[idxToCastToInt])
            except ValueError:
                return ' Invalid number of matches to return.\n' + usage
        else:
            numMatchesToRtn = 'all'

        startIdx = 0
        endIdx   = numLinesInFile-1
    ###########################
    else: # No match str specified.

        # Get/Calc number of lines to return (parmLst[0]).
        try:
            numLinesToRtnA = int(parmLst[0])
        except ValueError:
            return ' Invalid number of lines to read.\n' + usage

        numLinesToRtn = min(numLinesToRtnA, numLinesInFile)
        numLinesToRtn = max(numLinesToRtn,  1) # Don't allow reading <= 0 lines.

        # Get/Calc startIdx (parmLst[1]).
        if len(parmLst) > 1:
            try:
                startIdx = max(int(parmLst[1]),0) # Don't allow starting
            except ValueError:                    # before 0th line.
                return ' Invalid startIdx.\n' + usage

            if startIdx > numLinesInFile:
                startIdx=max( numLinesInFile - numLinesToRtn, 0 ) # Can't start
        else:                                                     # after EOF.
            startIdx = max(numLinesInFile - numLinesToRtn, 0)

        # Calc endIdx.
        endIdx = max(startIdx + numLinesToRtn - 1, 0)
        endIdx = min(endIdx, numLinesInFile-1)
    ###########################

    rspStr  = ' numLinesInFile  = {:4}.\n'.format( numLinesInFile  )
    rspStr += ' numMatchesToRtn = {:4}.\n'.format( numMatchesToRtn )
    rspStr += '  numLinesToRtn  = {:4}.\n'.format( numLinesToRtn   )
    rspStr += '       startIdx  = {:4}.\n'.format( startIdx        )
    rspStr += '         endIdx  = {:4}.\n'.format( endIdx          )
    rspStr += '       matchStr  = {}.\n\n'.format( matchStr        )

    if numMatchStr > 0:
        prevLine = '\n'
        prevIdx  = -1
        with open( inFile, 'r',encoding='utf-8') as f:
            for currIdx,currLine in enumerate(f):
                if startIdx <= currIdx <= endIdx:
                    if matchStr in currLine:
                        rspStr += ' {:4} - {}'.format(prevIdx,prevLine)
                        rspStr += ' {:4} - {}\n'.format(currIdx,currLine)
                    prevIdx  = currIdx
                    prevLine = currLine

    else:
        with open( inFile, 'r',encoding='utf-8') as f:
            for currIdx,currLine in enumerate(f):
                if startIdx <= currIdx <= endIdx:
                    rspStr += ' {:4} - {}'.format(currIdx,currLine)
                    prevIdx  = currIdx
                    prevLine = currLine

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

# No longer used, subsumed by python logger functionality.
#def writeFile(fName, inStr):
#    with open(fName, 'a', encoding='utf-8') as f:
#        f.write( inStr )
#        f.flush()
##############################################################################

if __name__ == '__main__':

    #            - return 5 lines starting from - 5th line from bottom.
    # 3          - return 3 lines starting from - 3rd line from bottom.
    # 3, 4       - return 3 lines starting from - line 4 (0 is 1st line).
    #
    # "match"    - return all lines with    "match" in it.
    # 3, "match" - return last 3 lines with "match" in it.

    while True:

        params = ['logFile.txt',['5']]

        inputStr = input( '--> ')
        inputWords = inputStr.split()

        if inputWords == []:       # In case user entered just spaces.
            print( 'no command entered' )
            continue

        choice     = inputWords[0]
        optArgsStr = inputWords[1:]

        if choice == 'q':
            break

        if choice != 'rlf':
            print( 'rlf not entered entered' )
            continue

        if len(optArgsStr) > 0:
            params[1] = optArgsStr

        #print(params)
        rsp = readFile( params )
        print()
        print(rsp[0])
