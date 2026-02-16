import threading as th # For handling multiple clients concurrently.
openSocketsLst = []    # Needed for processing close and ks commands.
procPidDict = {'clockCntrProc': None, 'lcdUpdateProc': None}
#############################################################################

def getActThrds():
    rspStr = ' Running Threads:\n'
    for t in th.enumerate():
        rspStr += '   {}\n'.format(t.name)

    rspStr += '\n Open Sockets:\n'
    for ii,openS in enumerate(openSocketsLst):

        rspStr+='   Socket {} Object Information \n'.format(ii)
        rspStr+='     Remote Addr, Port: {}\n'.format(openS['cs'].getpeername())
        rspStr+='      Local Addr, Port: {}\n'.format(openS['cs'].getsockname())
        rspStr+='       File descriptor: {}\n'.format(openS['cs'].fileno()     )
        rspStr+='              Protocol: {}\n'.format(openS['cs'].proto        )
        rspStr+='                Family: {}\n'.format(openS['cs'].family       )
        rspStr+='                  Type: {}\n'.format(openS['cs'].type         )

        rspStr+='   Socket {} Address Information \n'.format(ii)
        rspStr+='               Address: {}\n\n'.format(openS['ca'])

    rspStr += '\n Running Processes:\n'
    for k,v in procPidDict.items():
        if v is not None:
            rspStr += '   {}\n'.format(k)

    return [rspStr]
#############################################################################
