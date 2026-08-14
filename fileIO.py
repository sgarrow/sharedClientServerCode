import sys
import datetime as dt
#############################################################################

# Version number of the shared files.
# Calling it the version of the "server".
# As opposed to the version number of the "app" which is in cmdVectors.py
VER = 'v1.8.14 - 13-Aug-2026'

def splitList(parmLst):

    # starting parm list ['3', '"opened"']
    # end srch parm list ['opened']
    # end num parm list  ['3']
    #
    # starting parm list ['3', '"opened', 'at"']
    # end srch parm list ['opened at']
    # end num parm list  ['3']
    #
    # starting parm list ['3', '"opened', 'at"', '4', '"hello"',
    #                     '"multi', 'word', 'parm"', '9']
    # end srch parm list ['opened at', 'hello', 'multi word parm']
    # end num parm list  ['3', '4', '9']

    inDouble     = False
    builtMatch   = ''
    rspStr       = ''
    numStrLst    = []
    searchStrLst = []

    for el in parmLst:

        # Exit if error condition detected.
        if el == '""':
            rspStr = ' ERROR. Empty match string.'
            return rspStr, numStrLst, searchStrLst

        if el.startswith('"') and inDouble:
            rspStr =  ' ERROR. Nested double quotes.'
            return rspStr, numStrLst, searchStrLst

        # Add any simple parms.
        if not (el.startswith('"') or el.endswith('"')) and not inDouble:
            numStrLst.append(el)
            continue

        # Add any simple double quoted parms.
        if el.startswith('"') and el.endswith('"') and not inDouble:
            searchStrLst.append(el.strip('"'))
            continue

        # Should be able to set inDouble = True, if not it's an error.
        if el.startswith('"'):
            inDouble = True
            builtMatch = el.strip('"')
            continue

        # Continue to build the multi word search string.
        # Everyone above here either returns or continues.
        if inDouble:
            builtMatch +=  (' ' + el.strip('"'))
            if el.endswith('"'):
                searchStrLst.append(builtMatch)
                inDouble = False

    return rspStr, numStrLst, searchStrLst
#############################################################################

def readFileWrk(parmLst, inFile):

    usage = \
 '''
Example parameters:

 <NONE>    - return 5 lines starting from - 5th line from bottom.
 3         - return 3 lines starting from - 3rd line from bottom.
 3 4       - return 3 lines starting from - line 4 (0 is 1st line).
 
 "match"   - return all lines with    "match" in it.
 3 "match" - return last 3 lines with "match" in it.
 "match" 3 - return last 3 lines with "match" in it.
 "match" "this" 3 - return last 3 lines with "match" or "this"in it.

'''
    # Get total Lines in file.
    try:
        with open( inFile, 'r',encoding='utf-8') as f:
            numLinesInFile = sum(1 for line in f)
    except FileNotFoundError:
        return ' Could not open file {} for reading'.format(inFile)
    ###########################

    rspStr, numStrLst, searchStrLst = splitList(parmLst)

    if 'ERROR' in rspStr: # Empty or nested double quotes.
        return rspStr + usage

    isAllStrsAllDigits = all( s.isdigit() for s in numStrLst)

    if not isAllStrsAllDigits:
        return ' ERROR. not isAllStrsAllDigits.' + usage

    numIntLst  = [ int(x) for x in numStrLst ]

    # Verify correct number of parameters and if correct, init vars.
    numLinesToRtn   = 0 # Loop control when no match string supplied
    numMatchesToRtn = 0 # Loop control when  q match string supplied
    startIdx        = 0
    endIdx          = 0

    lenSearchStrLst = len( searchStrLst )
    lenNumStrLst    = len( numStrLst    )

    if lenNumStrLst == 0 and lenSearchStrLst == 0:
        rspStr  =  ' To few parameters.\n'
        rspStr +=  ' Not even the default parameter was received.'
        return rspStr

    if lenSearchStrLst > 0:
        startIdx = 0            # Match strings supplied.
        endIdx   = numLinesInFile-1
        if lenNumStrLst > 1:
            rspStr =  ' Too many parameters.\n'
            rspStr += ' When 1 or more double quoted search strings are\n'
            rspStr += ' supplied then only one digit, at most,'
            rspStr += ' (num matches to return) can be supplied.'
            return rspStr

        if lenNumStrLst == 0:
            # Loop control when no match string supplied.
            numMatchesToRtn = 'all'
        else:
            # Loop control when no match string supplied.
            numMatchesToRtn = numIntLst[0]

    else:                       # No match strings supplied.
        if lenNumStrLst > 2:
            rspStr =  ' Too many parameters.\n'
            rspStr += ' When no double quoted search string is\n'
            rspStr += ' supplied then only two digits, at most,\n'
            rspStr += ' (numLines to return and, optionally, the\n'
            rspStr += ' start log file index) can be supplied.'
            return rspStr

        numLinesToRtn = min(numIntLst[0], numLinesInFile) # Loop ctrl, no match str supplied.
        numLinesToRtn = max(numLinesToRtn, 1) # Don't allow reading <= 0 lines.

        if lenNumStrLst > 1:
            startIdx = max(int(numIntLst[1]),0) # Don't allow starting before 0th line.

            if startIdx > numLinesInFile:
                startIdx=max( numLinesInFile - numLinesToRtn, 0 ) # Can't start after EOF.
        else:
            startIdx = max(numLinesInFile - numLinesToRtn, 0)

        # Calc endIdx.
        endIdx = max(startIdx + numLinesToRtn - 1, 0)
        endIdx = min(endIdx, numLinesInFile-1)
    ###########################

    rspStr  = ' numLinesInFile  = {:4}.\n'.format( numLinesInFile  )
    if lenSearchStrLst > 0:
        matchDict = {}
        ii        = 0
        prevLine  = '\n'
        prevIdx   = -1
        with open( inFile, 'r',encoding='utf-8') as f:
            for currIdx,currLine in enumerate(f):
                if startIdx <= currIdx <= endIdx:
                    if any(el in currLine for el in searchStrLst):
                        dicStr  = ' {:4} - {}'.format(prevIdx,prevLine)
                        dicStr += ' {:4} - {}\n'.format(currIdx,currLine)
                        matchDict[ii] = dicStr
                        ii += 1
                    prevIdx  = currIdx
                    prevLine = currLine

        if numMatchesToRtn == 'all':
            numMatchesToRtn = len(matchDict)

        startIdx = max( len( matchDict ) - numMatchesToRtn, 0 )
        endIdx   = len( matchDict )
        for ii in range( startIdx, endIdx ):
            rspStr += matchDict[ii]
        rspStr += ' Returned the last {} of {} matches found.'.\
            format(endIdx-startIdx, len(matchDict))

    else:
        with open( inFile, 'r',encoding='utf-8') as f:
            for currIdx,currLine in enumerate(f):
                if startIdx <= currIdx <= endIdx:
                    rspStr += ' {:4} - {}'.format(currIdx,currLine)

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

if __name__ == '__main__':

    while True:

        params = ['logFile.txt',['5']]

        inputStr = input( '--> ')
        inputWords = inputStr.split()

        if inputWords == []: # In case user entered just spaces.
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

        rsp = readFile( params )
        print()
        print(rsp[0])
