
#############################################################################

def getCfgDict(uut):
    cfgDict = {}
    rspStr  = ''
    try:
        with open('cfg.cfg', 'r', encoding='utf-8') as f:
            for line in f:
                # If not a comment line and line is not all whitespace
                if '#' not in line and line.strip():
                    lSplit = line.split()
                    if len(lSplit) == 5:
                        tmpDict = {}
                        tmpDict[ 'myPort'  ] = lSplit[1]
                        tmpDict[ 'myLan'   ] = lSplit[2]
                        tmpDict[ 'myIP'    ] = lSplit[3]
                        tmpDict[ 'myPwd'   ] = lSplit[4]
                        cfgDict[ lSplit[0] ] = tmpDict
                    else:
                        rspStr += ' ERROR. Line does not contain 5 items:\n {}\n'\
                            .format(line.strip())
    except FileNotFoundError:
        rspStr += ' ERROR. File cfg.cfg not found.\n'

    # Verify port values
    allPorts = [ v['myPort'] for v in cfgDict.values() ]
    allPortsAreInts = all(s.isdigit() for s in allPorts)
    if not allPortsAreInts:
        rspStr += ' ERROR. Non-digit character detected in port number:\n {}\n'.\
            format(allPorts)

    allLanIps    = [ v['myLan'].split('.') for v in cfgDict.values() ]
    allRouterIps = [ v['myIP' ].split('.') for v in cfgDict.values() ]
    allIps       = [ allLanIps, allRouterIps ]

    # Verify Lan and router IP lengths
    for lanOrRouterIp in allIps:
        for ip in lanOrRouterIp:
            if len(ip) != 4:
                rspStr += ' ERROR. Invalid lengtth detected in LAN or Router IP:\n {}\n'.\
                    format(lanOrRouterIp)

    # Verify Lan and router IP values
    for lanOrRouterIp in allIps:
        for ip in lanOrRouterIp:
            allIpsAreInts = all(s.isdigit() for s in ip)
            if not allIpsAreInts:
                rspStr += ' ERROR. Non-digit character detected in LAN or Router IP:\n {}\n'.\
                    format(lanOrRouterIp)

    # Verify the uut key is in main dict.
    if uut not in cfgDict:
        rspStr += ' ERROR. Sub-Dict {} not found.\n'.format(uut)

    return rspStr, cfgDict
#############################################################################

if __name__ == '__main__':
    pass
    #import pprint as pp
    #import sys
    #arguments  = sys.argv
    #scriptName = arguments[0]
    #userArgs   = arguments[1:]
    #mnUut      = userArgs[0]
    #
    #mnRspStr, mnCfgDict = getCfgDict(mnUut)
    #
    #pp.pprint(mnCfgDict)
    #
    #if 'ERROR' in mnRspStr:
    #    print('\n Missing or (malformed) cfg file or missing cmd line arg')
    #    print(' usage1: python client.py uut (uut = spr or clk).')
    #    print(mnRspStr)
