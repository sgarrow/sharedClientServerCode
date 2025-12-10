import sys                    # For getting command line args.
import os                     # For rebooting.
import socket                 # For creating and managing sockets.
import threading       as th  # For handling multiple clients concurrently.
import queue                  # For Killing Server.
import time                   # For Killing Server and listThreads.
import datetime        as dt  # For logging server start/stop times.
import cmdVectors      as cv  # For vectoring to worker functions.
import cfg                    # For port, pwd.
import fileIO          as fio # For writing to server log files.
import utils           as ut  # For access to openSocketsLst[].
import serverCustomize as sc  # For stopping clock at shutdown (ks or rbt).
#############################################################################

def processCloseCmd( parmDict ):

    clientSocket      = parmDict['clientSocket']
    clientAddress     = parmDict['clientAddress']

    rspStr = ' handleClient {} set loop break RE: close \n'.format(clientAddress)
    clientSocket.send(rspStr.encode()) # sends all even if >1024.
    time.sleep(1) # Required so .send happens before socket closed.
    # Breaks the loop, connection closes and thread stops.
    ut.openSocketsLst.remove({'cs':clientSocket,'ca':clientAddress})
    return rspStr
#############################################################################

def processKsAndRbtCmds( parmDict ):

    clientSocket      = parmDict['clientSocket']
    clientAddress     = parmDict['clientAddress']
    client2ServerCmdQ = parmDict['client2ServerCmdQ']
    styleDict         = parmDict['styleDict']
    styleDictLock     = parmDict['styleDictLock']
    #uut               = parmDict['uut']
    reboot            = parmDict['reboot']

    rspStr = ''

    if reboot:
        tmpStr = 'rbt'
    else:
        tmpStr = 'ks'

    # Client sending ks has to be terminated first, I don't know why.
    rspStr += sc.ksCleanup(styleDict, styleDictLock)
    rspStr += '\n handleClient {} set loop break for self RE: {} \n'.\
              format(clientAddress,tmpStr)
    clientSocket.send(rspStr.encode()) # sends all even if > 1024.
    time.sleep(1.5) # Required so .send happens before socket closed.

    # Breaks the ALL loops, ALL connections close and ALL thread stops.
    for el in ut.openSocketsLst:
        if el['ca'] != clientAddress:
            rspStr += ' handleClient {} set loop break for {} RE: {} \n'.\
                format(clientAddress, el['ca'], tmpStr)
            el['cs'].send(rspStr.encode()) # sends all even if > 1024.
            time.sleep(1) # Required so .send happens before socket closed.

    rspStrNew  = rspStr.replace(   'ks', 'KS' ) # Prevent client break RE: rsl
    rspStrNew2 = rspStrNew.replace('rbt','RBT') # Prevent client break RE: rsl

    ut.openSocketsLst.clear()     # Causes all clients to terminate.
    client2ServerCmdQ.put(tmpStr) # Causes the server to terminate and may
                                  # also cause the RPi to reboot.

    return rspStrNew2
#############################################################################

def updateDict(inDict, **kwargs):
    new = inDict.copy()
    new.update(kwargs)
    return new

def handleClient( argDict ):

    clientSocket      = argDict['clientSocket']
    clientAddress     = argDict['clientAddress']
    #client2ServerCmdQ = argDict['client2ServerCmdQ']
    styleDict         = argDict['styleDict']
    styleDictLock     = argDict['styleDictLock']
    uut               = argDict['uut']

    rebootArgDict = updateDict( argDict, reboot = True )
    noRebtArgDict = updateDict( argDict, reboot = False )

    vectorDict = {
    'close': { 'fun': processCloseCmd,     'prm': noRebtArgDict },
    'ks'   : { 'fun': processKsAndRbtCmds, 'prm': noRebtArgDict },
    'rbt'  : { 'fun': processKsAndRbtCmds, 'prm': rebootArgDict }
    }

    rspStr = ''
    # Validate password
    cfgRspStr, cfgDict = cfg.getCfgDict(uut)
    data = clientSocket.recv(1024)
    if data.decode() == cfgDict[uut]['myPwd']:
        passwordIsOk = True
        rspStr += ' Accepted connection from: {}\n'.format(clientAddress)
    else:
        passwordIsOk = False
        rspStr += ' Rejected connection from: {}\n'.format(clientAddress)

    fio.writeFile('serverLog.txt', rspStr)
    clientSocket.send(rspStr.encode()) # sends all even if >1024.

    if passwordIsOk:
        clientSocket.settimeout(3.0)   # Set .recv timeout - ks processing.
        ut.openSocketsLst.append({'cs':clientSocket,'ca':clientAddress})

    # The while condition is made false by the close, ks and rbt commands.
    while {'cs':clientSocket,'ca':clientAddress} in ut.openSocketsLst:

        logStr = ''
        # Recieve msg from the client (and look (try) for UNEXPECTED EVENT).
        try: # In case user closed client window (x) instead of by close cmd.
            data = clientSocket.recv(1024) # Broke if any msg > 1024.
            #print(' data.decode() = **{}**'.format(data.decode()))

        except ConnectionResetError: # Windows throws this on (x).
            logStr += ' handleClient {} ConnectRstErr except in s.recv\n'.format(clientAddress)
            # Breaks the loop. handler/thread stops. Connection closed.
            ut.openSocketsLst.remove({'cs':clientSocket,'ca':clientAddress})
            break
        except ConnectionAbortedError: # Test-NetConnection xxx.xxx.x.xxx -p xxxx throws this
            logStr += ' handleClient {} ConnectAbtErr except in s.recv\n'.format(clientAddress)
            ut.openSocketsLst.remove({'cs':clientSocket,'ca':clientAddress})
            break
        except socket.timeout: # Can't block on recv - won't be able to break
            continue           # loop if another client has issued a ks cmd.

        # Getting here means a command has been received.
        logStr = ' handleClient {} received: {}\n'.\
            format(clientAddress, data.decode())
        print(logStr)

        if data.decode().split()[0] in vectorDict:
            func    = vectorDict[data.decode().split()[0]]['fun']
            params  = vectorDict[data.decode().split()[0]]['prm']
            logStr += func(params)

        # Process up special message and send response back to this client.
        elif data.decode().split()[0] in sc.specialCmds: # up fPath numBytes
            inParms  = data.decode().split()
            response = sc.specialCmdHndlr( inParms, clientSocket )
            clientSocket.send(response.encode())

        # Process a normal message and send response back to this client.
        # (and look (try) for UNEXPECTED EVENT).
        else:
            response = cv.vector(data.decode(),styleDict, styleDictLock)
            try: # If user closed client window (x) instead of by close cmd.
                clientSocket.send(response.encode())
            except BrokenPipeError:      # RPi throws this on (x).
                logStr +=' handleClient {} BrokePipeErr except in s.send\n'.\
                    format(clientAddress)
                # Breaks the loop. handler/thread stops. Connection closed.
                ut.openSocketsLst.remove({'cs':clientSocket,'ca':clientAddress})

        if logStr != '':
            fio.writeFile('serverLog.txt', logStr)

    logStr = ' handleClient {} closing socket and breaking loop\n'.format(clientAddress)
    fio.writeFile('serverLog.txt', logStr)
    clientSocket.close()
#############################################################################

def printSocketInfo(sSocket):
    sndBufSize = sSocket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    rcvBufSize = sSocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    rspStr = ' sndBufSize = {} \n rcvBufSize = {}\n'.format(sndBufSize,rcvBufSize)
    return rspStr # 64K
#############################################################################

def startServer(uut):
    now = dt.datetime.now()
    cDT = '{}'.format(now.isoformat( timespec = 'seconds' ))
    logStr =  'Server started at {} \n'.format(cDT)
    fio.writeFile('serverLog.txt', logStr)

    styleDict, styleDictLock = sc.getMultiProcSharedDict()

    host = '0.0.0.0'  # Listen on all available interfaces
    rspStr, cfgDict = cfg.getCfgDict(uut)
    port = int(cfgDict[uut]['myPort'])

    serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # This line makes it so you can kill the server and then restart it right
    # away.  Without this you get an error until the socket eventually is
    # complete closed by th os. Here's the error you get without this:
    #
    #  File "/home/pi/python/spiClock/server.py", line 204, in <module>
    #  startServer()
    #  File "/home/pi/python/spiClock/server.py", line 145, in startServer
    #  serverSocket.bind((host, port))
    #  OSError: [Errno 98] Address already in use
    serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    serverSocket.bind((host, port))
    serverSocket.listen(5)
    serverSocket.settimeout(3.0) # Sets the .accept timeout - ks processing.

    clientToServerCmdQ = queue.Queue() # So client can tell server to stop.

    logStr  = 'Server listening on: {} {}\n'.format(host, port)
    logStr += printSocketInfo(serverSocket)
    fio.writeFile('serverLog.txt', logStr)
    # sndBufSize =  16,384  # 0.25 * 64K
    # rcvBufSize = 131,072  # 2.00 * 64K

    while True:
        logStr = ''
        # See if any client has requested the server to halt (ks command).
        try:
            cmd = clientToServerCmdQ.get(timeout=.1)
        except queue.Empty:
            pass
        else:
            if cmd in ['ks','rbt']:
                # Wait for all clients to terminate
                threadLst = [ t.name for t in th.enumerate() ]
                while any(el.startswith('handleClient-') for el in threadLst):
                    threadLst = [ t.name for t in th.enumerate() ]
                    time.sleep(.1)
                break

        # See if any new clients are trying to connect.
        try:
            clientSocket, clientAddress = serverSocket.accept()
        except socket.timeout: # Can't block on accept - won't be able to
            continue           # break loop if a client has issued a ks cmd.
        else:
            # Yes, create a new thread to handle the new client.
            logStr += 'Starting a new client handler thread.\n'

            argsDict = { 'clientSocket':       clientSocket,
                         'clientAddress':      clientAddress,
                         'client2ServerCmdQ': clientToServerCmdQ,
                         'styleDict':          styleDict,
                         'styleDictLock':      styleDictLock,
                         'uut':                uut } 

            cThrd= th.Thread(target= handleClient,
                             args  = ( argsDict, ),
                             name  = 'handleClient-{}'.format(clientAddress))
            cThrd.start()

        if logStr != '':
            fio.writeFile('serverLog.txt', logStr)

    logStr = 'Server breaking.\n'
    serverSocket.close()

    now = dt.datetime.now()
    cDT = '{}'.format(now.isoformat( timespec = 'seconds' ))
    logStr += 'Server stopped at {} \n'.format(cDT)
    fio.writeFile('serverLog.txt', logStr)

    if cmd == 'rbt':
        #print('rebooting')
        # Trigger async reboot
        th.Thread(target=lambda: os.system('sleep 3 && sudo reboot'), daemon=True).start()
    else:
        pass
        #print('not rebooting')

#############################################################################

def getLanIp():
    """
    Attempts to determine the local LAN IP address of the machine.
    This method works by connecting to an external server (like Google's DNS)
    and then retrieving the local IP address used for that connection.
    """
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Connect to an external address (Google's public DNS server)
        # This connection is not established, but it forces the socket
        # to bind to a local interface, allowing us to get its address.
        s.connect(('8.8.8.8', 80))

        # Get the local IP address of the socket
        lanIp = s.getsockname()[0]

        # Close the socket
        s.close()

        return lanIp
    except Exception as e:
        print(e)
        return None
#############################################################################

if __name__ == '__main__':

    arguments  = sys.argv
    scriptName = arguments[0]
    mnUut      = None            # pylint: disable=C0103
    mnCfgDict  = None            # pylint: disable=C0103
    if len(arguments) >= 2:
        userArgs   = arguments[1:]
        mnUut      = userArgs[0]
        mnCfgDict  = cfg.getCfgDict(mnUut) # pylint: disable=C0103

    if mnUut is None or mnCfgDict is None:
        print('  Server not started.')
        print('  Missing or (malformed) cfg file or')
        print('  Missing or (malformed) cmd line arg')
        print('  usage1: python server.py uut (uut = spr, clk, clk2).')
        sys.exit()
    else:
        sc.hwInit()
        mnLanIp = getLanIp()
        sc.displayLanIp(mnLanIp)

    startServer(mnUut)
