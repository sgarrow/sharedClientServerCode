import sys                    # For getting command line args.
import os                     # For rebooting.
import socket                 # For creating and managing sockets.
import logging         as lg
import threading       as th  # For handling multiple clients concurrently.
import queue                  # For Killing Server.
import time                   # For Killing Server and listThreads.
import datetime        as dt  # For logging server start/stop times.
import cmdVectors      as cv  # For vectoring to worker functions.
import cfg                    # For port, pwd.
import utils           as ut  # For access to openSocketsLst[].
import serverCustomize as sc  # For stopping clock at shutdown (ks or rbt).
#############################################################################

def processCloseCmd( parmDict ):

    clientSocket      = parmDict['clientSocket']
    clientAddress     = parmDict['clientAddress']

    rspStr = ' handleClient {} set loop break RE: CLOSE \n'.format(clientAddress)
    clientSocket.send(rspStr.encode()) # sends all even if >1024.
    time.sleep(1) # Required so .send happens before socket closed.
    ut.openSocketsLst.remove({'cs':clientSocket,'ca':clientAddress})
    return rspStr
#############################################################################

def processKsAndRbtCmds( parmDict ):

    clientSocket      = parmDict['clientSocket']
    clientAddress     = parmDict['clientAddress']
    client2ServerCmdQ = parmDict['client2ServerCmdQ']
    mpSharedDict      = parmDict['mpSharedDict']
    mpSharedDictLock  = parmDict['mpSharedDictLock']
    #uut               = parmDict['uut']
    reboot            = parmDict['reboot']

    rspStr = ''

    if reboot:
        tmpStr = 'rbt'
    else:
        tmpStr = 'ks'

    # Client sending ks has to be terminated first, I don't know why.
    rspStr += sc.ksCleanup(mpSharedDict, mpSharedDictLock)
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
            print(rspStr)
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
#############################################################################

def validatePwdSendRsp( uut, clientSocket, clientAddress ):

    cfgRspStr, cfgDict = cfg.getCfgDict(uut) # pylint: disable=W0612
    data = clientSocket.recv(1024)

    if data.decode() == cfgDict[uut]['myPwd']:
        passwordIsOk = True
        rspStr = 'Accepted connection from: {}'.format(clientAddress)
    else:
        passwordIsOk = False
        rspStr = 'Rejected connection from: {}'.format(clientAddress)

    lg.info( rspStr )
    clientSocket.send(rspStr.encode()) # sends all even if >1024.
    return passwordIsOk
#############################################################################

def handleClient( argDict ):

    clientSocket      = argDict['clientSocket']
    clientAddress     = argDict['clientAddress']
    #client2ServerCmdQ = argDict['client2ServerCmdQ']
    #mpSharedDict      = argDict['mpSharedDict']
    #mpSharedDictLock  = argDict['mpSharedDictLock']
    #uut               = argDict['uut']

    rebootArgDict = updateDict( argDict, reboot = True )
    noRebtArgDict = updateDict( argDict, reboot = False )

    vectorDict = {
    'close': { 'fun': processCloseCmd,     'prm': noRebtArgDict },
    'ks'   : { 'fun': processKsAndRbtCmds, 'prm': noRebtArgDict },
    'rbt'  : { 'fun': processKsAndRbtCmds, 'prm': rebootArgDict }
    }
    passwordIsOk = validatePwdSendRsp( argDict['uut'],
                                       clientSocket,
                                       clientAddress
                                     )
    if passwordIsOk:
        clientSocket.settimeout(3.0)   # Set .recv timeout - ks processing.
        ut.openSocketsLst.append({'cs':clientSocket,'ca':clientAddress})

    # The while condition is made false by the close, ks and rbt commands.
    while {'cs':clientSocket,'ca':clientAddress} in ut.openSocketsLst:

        # Recieve msg from the client (and look (try) for UNEXPECTED EVENT).
        try: # In case user closed client window (x) instead of by close cmd.
            data       = clientSocket.recv(1024) # Broke if any msg > 1024.
            dataDecode = data.decode()
            splitData  = dataDecode.split()
            cmd        = splitData[0]

        except IndexError:
            lg.exception('handleClient %s IndexError except in s.recv',clientAddress)
            continue
        except ConnectionResetError:   # Windows throws this on (x).
            lg.exception('handleClient %s ConnectRstErr except in s.recv',clientAddress)
            break
        except ConnectionAbortedError: # Test-NetConnection xxx.xxx.x.xxx -p xxxx throws this
            lg.exception('handleClient %s ConnectAbtErr except in s.recv',clientAddress)
            break
        except socket.timeout: # Can't block on recv - won't be able to break
            continue           # loop if another client has issued a ks cmd.

        # Getting here means a command has been received.
        lg.info( 'handleClient %s received: %s',clientAddress, dataDecode )
        print(   'handleClient %s received: %s',clientAddress, dataDecode )

        # Process close, ks, rbt cmds and send response back to this client.
        if cmd in vectorDict:
            func   = vectorDict[cmd]['fun']
            params = vectorDict[cmd]['prm']
            lg.info( func(params) )

        # Process up special message and send response back to this client.
        if cmd in sc.specialCmds: # up fPath numBytes
            response = sc.specialCmdHndlr( splitData, clientSocket )
            clientSocket.send(response.encode())

        # Process a normal message and send response back to this client.
        else:
            response = cv.vector( dataDecode,
                                  argDict['mpSharedDict'],
                                  argDict['mpSharedDictLock']
                                )
            try: # If user closed client window (x) instead of by close cmd.
                clientSocket.send(response.encode())
            except BrokenPipeError:      # RPi throws this on (x).
                lg.exception('handleClient %s BrokePipeErr except in s.send',clientAddress)
                break

    if {'cs':clientSocket,'ca':clientAddress} in ut.openSocketsLst:
        ut.openSocketsLst.remove({'cs':clientSocket,'ca':clientAddress})
    lg.info( 'handleClient %s closing socket and breaking loop\n',clientAddress)
    clientSocket.close()
#############################################################################

def logSocketInfo(sSocket):
    sndBufSize = sSocket.getsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF)
    rcvBufSize = sSocket.getsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF)
    lg.info( 'sndBufSize = %s, rcvBufSize = %s',sndBufSize,rcvBufSize)
#############################################################################

def startServer(uut):
    now = dt.datetime.now()
    cDT = '{}'.format(now.isoformat( timespec = 'seconds' ))
    lg.info( 'Server started at %s', cDT)

    mpSharedDict, mpSharedDictLock = sc.getMultiProcSharedDictAndLock()

    host = '0.0.0.0'  # Listen on all available interfaces
    rspStr, cfgDict = cfg.getCfgDict(uut) # pylint: disable=W0612
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

    lg.info( 'Server listening on: %s %s', host, port)
    logSocketInfo(serverSocket)

    while True:
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
            lg.info( 'Starting a new client handler thread.' )

            argsDict = { 'clientSocket':       clientSocket,
                         'clientAddress':      clientAddress,
                         'client2ServerCmdQ':  clientToServerCmdQ,
                         'mpSharedDict':       mpSharedDict,
                         'mpSharedDictLock':   mpSharedDictLock,
                         'uut':                uut } 

            cThrd= th.Thread(target= handleClient,
                             args  = ( argsDict, ),
                             name  = 'handleClient-{}'.format(clientAddress))
            cThrd.start()

    lg.info( 'Server breaking.')
    serverSocket.close()

    now = dt.datetime.now()
    cDT = '{}'.format(now.isoformat( timespec = 'seconds' ))
    lg.info( 'Server stopped at %s', cDT)

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
    except Exception as e: # pylint: disable=W0718
        print(e)
        return None
#############################################################################
def main():

    lg.basicConfig(
        filename='serverLog.txt',
        level=lg.INFO,
        format='%(asctime)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    #lg.info(      'Test info message.'     )
    #lg.warning(   'Test warning message.'  )
    #lg.error(     'Test error message.'    )
    #lg.critical(  'Test critical message.' )
    #lg.exception( 'Test exception mesage.' )
    #lg.debug(     'Test debug message.'    )

    arguments  = sys.argv
    #scriptName = arguments[0]
    mnUut      = None                      # pylint: disable=C0103
    mnCfgDict  = None                      # pylint: disable=C0103
    if len(arguments) >= 2:
        userArgs   = arguments[1:]
        mnUut      = userArgs[0]
        mnCfgDict  = cfg.getCfgDict(mnUut) # pylint: disable=C0103

    if mnUut is None or mnCfgDict is None:
        msg  = ''
        msg += 'Server not started.'
        msg += '\nMissing or (malformed) cfg file or'
        msg += '\nMissing or (malformed) cmd line arg'
        msg += '\nusage1: python server.py uut (uut = spr, clk, clk2).\n'
        print( msg )
        lg.error( msg )
        sys.exit()
    else:
        sc.hwInit()
        mnLanIp = getLanIp()
        sc.displayLanIp(mnLanIp)

    startServer(mnUut)
#############################################################################

if __name__ == '__main__':
    main()
