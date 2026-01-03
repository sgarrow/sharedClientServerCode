'''
This is the user interface to the server.  All of the files in this project
must be on the RPi except this one although it may/can also be on the RPi.

This file can be run on the Rpi, a PC or a phone.
'''

try:
    import readline  # pylint: disable=W0611
except (ModuleNotFoundError, AttributeError):
    pass
    #print('\n Exception importing readline. ok to continue.\n')

import sys
import socket
import time
import select
import threading
import queue
import cfg
import clientCustomize as cc
#############################################################################

def printSocketInfo(cSocket):
    sndBufSize = cSocket.getsockopt( socket.SOL_SOCKET, socket.SO_SNDBUF )
    rcvBufSize = cSocket.getsockopt( socket.SOL_SOCKET, socket.SO_RCVBUF )
    print( ' sndBufSize', sndBufSize ) # 64K
    print( ' rcvBufSize', rcvBufSize ) # 64K
#############################################################################

def sendCmd( tLock, cmdQ ):
    userInput = ''
    breakCmds = ['ks','close','rbt']
    specialDict     = { 'clk':['up'],             # Special cmds.
                        'spr':['dummy'] }
    while True:
        with tLock:
            prompt = '\n Choice (m=menu, close) -> '

            message = input( prompt )
            msgLst  = message.split()
    
            if  'Clock'      in uut and len(msgLst) > 0 and \
                msgLst[0].lstrip() in specialDict['clk']:
                # Send special message.
                cc.processSpecialCmd('uploadPic',clientSocket,msgLst)
    
            elif 'Sprinkler' in uut and len(msgLst) > 0 and \
                msgLst[0].lstrip() in specialDict['spr']:
                # Send special message.
                cc.processSpecialCmd('dummy',clientSocket,msgLst)
    
            else:
                # Send normal message.
                clientSocket.send(message.encode())

            cmdQ.put('readRsp')
    
        time.sleep(.01)
        if  len(msgLst) > 0 and msgLst[0] in breakCmds:
            break
#############################################################################

def readRsp( tLock, cmdQ ):

    exitStrings = ['RE: close', 'RE: ks', 'RE: rbt']

    while True:

        message = cmdQ.get()    # Get/send msg from Q. Blocks.
        with tLock:

            rspStr = ''
            readyToRead, _, _ = select.select([clientSocket],[],[],20)
            if readyToRead:
    
                while readyToRead:
    
                    response = clientSocket.recv(1024)
                    rspStr += response.decode()
    
                    # No more data if server is being terminated.
                    if any(word in rspStr for word in exitStrings): # Exit.
                        break
    
                    readyToRead,_, _=select.select([clientSocket],[],[],.01)
    
                    print('\n{}'.format(rspStr),flush = True)
                time.sleep(.01)
            else:
                print( ' Timeout waiting for response.')

        if any(word in rspStr for word in exitStrings): # Exit.
            break

    print('\n Client closing Socket')
    time.sleep(.01)
    clientSocket.close()
#############################################################################

if __name__ == '__main__':

    arguments  = sys.argv
    scriptName = arguments[0]
    userArgs   = arguments[1:]
    uut        = userArgs[0]
    cfgRspStr, cfgDict = cfg.getCfgDict(uut)

    if 'ERROR' in cfgRspStr:
        print('\n Missing or (malformed) cfg file or missing cmd line arg')
        print(' usage1: python client.py uut (uut = spr or clk).')
        print(cfgRspStr)
        sys.exit()

    # Each client will connect to the server with a new address.
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    #connectType = input(' same, lan, internet (s,l,i) -> ')
    connectType  = 'l' # pylint: disable=C0103
    connectDict  = {'s':'localhost',
                    'l':cfgDict[uut]['myLan'],
                    'i':cfgDict[uut]['myIP']}
    PORT         = int(cfgDict[uut]['myPort'])

    try:
        clientSocket.connect((connectDict[connectType], PORT ))
    except ConnectionRefusedError:
        print('\n ConnectionRefusedError.  Ensure server is running.\n')
        sys.exit()
    except socket.timeout:
        print('\n TimeoutError.  Ensure server is running.\n')
        sys.exit()

    printSocketInfo(clientSocket)

    # Validate password
    pwd = cfgDict[uut]['myPwd']
    clientSocket.send(pwd.encode())
    #clientSocket.send('xx'.encode())
    time.sleep(.5)
    response = clientSocket.recv(1024)
    rspStr   = response.decode()
    print('\n{}'.format(rspStr))
    pwdIsOk = 'Accepted' in rspStr

    if pwdIsOk:
        threadLock = threading.Lock()
        commandQ   = queue.Queue()
        sendCmdThread = threading.Thread( target = sendCmd,
                                          args   = (threadLock,commandQ),
                                          daemon = False )
    
        readRspThread = threading.Thread( target = readRsp,
                                          args   = (threadLock,commandQ),
                                          daemon = False )
        sendCmdThread.start()
        readRspThread.start()
