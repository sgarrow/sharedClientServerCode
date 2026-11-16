'''
This is the user interface to the server.
This file can be run on the Rpi, a PC or a phone.
'''

try:
    import readline  # pylint: disable=W0611
except (ModuleNotFoundError, AttributeError):
    pass
    #print('\n Exception importing readline. ok to continue.\n')

import sys
import time
import queue
import socket
import select
import threading
import pprint as pp

import cfg
import clientCustomize as cc
#############################################################################

def printSocketInfo(cSocket):
    sndBufSize = cSocket.getsockopt( socket.SOL_SOCKET, socket.SO_SNDBUF )
    rcvBufSize = cSocket.getsockopt( socket.SOL_SOCKET, socket.SO_RCVBUF )
    print( ' sndBufSize', sndBufSize ) # 64K
    print( ' rcvBufSize', rcvBufSize ) # 64K
#############################################################################

def sendCmd( uut, clientSock, tLock, cmdQ ):

    breakCmds   = ['ks','close','rbt']
    specialDict = { 'clk':['up'], 'spr':['tmp'] }

    specialCmdLst = []
    if 'Clock'    in uut: specialCmdLst = specialDict['clk']
    if 'Sprinkler' in uut: specialCmdLst = specialDict['spr']

    while True:
        exceptionOccured = False
        with tLock:
            #print(' {} - got lock'.format('sendCmd'))
            prompt  = '\n Choice (m=menu, close) -> '
            message = input( prompt )
            msgLst  = message.split()

            #print('*{}*'.format(message))
            #print(msgLst )
            if msgLst == []:
                continue

            if  msgLst[0].lstrip() in specialCmdLst:
                # Send special message.
                cc.processSpecialCmd(msgLst[0].lstrip(),clientSock,msgLst)
                continue  # Skip cmdQ.put, go back to show next prompt

            # Send normal message (if not continued ... from above.
            try:
                clientSock.send(message.encode())
                cmdQ.put({ 'readRsp':True, 'shouldExit': msgLst[0] in breakCmds })
            except OSError:
                exceptionOccured = True


        #print(' {} - release lock'.format('sendCmd'))
        time.sleep(.01)
        if  (len(msgLst) > 0 and msgLst[0] in breakCmds) or exceptionOccured:
            #print(' {} - breaking.'.format('sendCmd'))
            break
#############################################################################

def readRsp( clientSock, tLock, cmdQ ):

    response = '?'
    while True:

        message = cmdQ.get()    # Get/send msg from Q. Blocks.
        if message['readRsp']:
            with tLock:

                #print(' {} - got lock'.format('readRsp'))
                rspStr = ''
                readyToRead, _, _ = select.select([clientSock],[],[],20)
                if readyToRead:

                    while readyToRead:

                        try:
                            response = clientSock.recv(1024)
                        except (ConnectionAbortedError,ConnectionResetError): #ks
                            message['shouldExit'] = True
                            print( response )

                        #print( ' {} - received {} bytes.'.format('readRsp',len(response)))
                        rspStr += response.decode()

                        # No more data if server is being terminated.
                        if message['shouldExit']:
                            break

                        readyToRead,_, _=select.select([clientSock],[],[],.01)

                    print('\n{}'.format(rspStr),flush = True)
                    time.sleep(.01)
                else:
                    print( ' Timeout waiting for response.')

            if message['shouldExit']:
                break
            #print(' {} - release lock'.format('readRsp'))
        else:
            print( ' Unrecognized command in cmdQ.')

    #print(' {} - breaking.'.format('readRsp'))
    print('\n {} - Client closing Socket'.format('readRsp'))
    time.sleep(.01)
    clientSock.close()
#############################################################################

if __name__ == '__main__':

    arguments  = sys.argv
    scriptName = arguments[0]
    userArgs   = arguments[1:]

    if len(userArgs) == 0:
        cfgRspStr, cfgDict = cfg.getCfgDict('')
        selUutDict = { k:v for k,v in enumerate(cfgDict) }
        print()
        for k,v in selUutDict.items():
            print(' {} - {}'.format(k,v))
        validChoice = False
        while not validChoice:
            uutToConnectTo = input('\n Select UUT to connect to (or (q)uit) -> ')
            if uutToConnectTo == 'q':
                print()
                sys.exit()
            try:
                uutToConnectToInt = int(uutToConnectTo)
            except:
                print(' Invalid selection. Enter a number in range 0 to {}'.format(len(selUutDict)-1))
            else:
                if -1 < uutToConnectToInt < len(selUutDict):
                    validChoice = True
                else:
                    print(' Invalid selection. Enter a number in range 0 to {}'.format(len(selUutDict)-1))
        mnUut = selUutDict[int(uutToConnectToInt)]
    else:
        mnUut  = userArgs[0]

    cfgRspStr, cfgDict = cfg.getCfgDict(mnUut)

    if 'ERROR' in cfgRspStr:
        print('\n Missing or (malformed) cfg file or missing cmd line arg')
        print(' usage1: python client.py uut (uut = spr or clk).')
        print(cfgRspStr)
        sys.exit()

    # Each client will connect to the server with a new address.
    clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    connectType = input(' same, lan, internet, lan exact (s,l,i,lx,q) -> ')

    if connectType == 'q':
        print()
        sys.exit()

    #connectType  = 'l' # pylint: disable=C0103
    connectDict  = {'s':'localhost',
                    'l':cfgDict[mnUut]['myLan'],
                    'i':cfgDict[mnUut]['myIP']}
    PORT         = int(cfgDict[mnUut]['myPort'])

    if connectType == 'lx':
        connectDict['l'] = input( 'Enter LAN IP -> ' )
        connectType = 'l'

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
    pwd = cfgDict[mnUut]['myPwd']
    clientSocket.send(pwd.encode())
    #clientSocket.send('xx'.encode())
    time.sleep(.5)
    rsp      = clientSocket.recv(1024)
    mnRspStr = rsp.decode()
    print('\n{}'.format(mnRspStr))
    pwdIsOk = 'Accepted' in mnRspStr

    if pwdIsOk:
        threadLock = threading.Lock()
        commandQ   = queue.Queue()
        sendCmdThread = threading.Thread( target =   sendCmd,
                                          args   = ( mnUut,
                                                     clientSocket,
                                                     threadLock,
                                                     commandQ),
                                          daemon =   False )

        readRspThread = threading.Thread( target =   readRsp,
                                          args   = ( clientSocket,
                                                     threadLock,
                                                     commandQ),
                                          daemon = False )
        sendCmdThread.start()
        readRspThread.start()
    else:
        print('\n {} - Client closing Socket'.format('main'))
        clientSocket.close()
