
#############################################################################

def getCfgDict(uut):
    #print(uut)
    requiredKeys = ['myLan', 'myIP', 'myPort', 'myPwd']
    cfgDict = {}
    try:
        with open('cfg.cfg', 'r', encoding='utf-8') as f:
            for line in f:
                if '#' not in line and line.strip():
                    lSplit = line.split()
                    if len(lSplit) == 4 and lSplit[0] == uut:
                        cfgDict[lSplit[1]] = lSplit[3]
    except FileNotFoundError:
        return None

    if not all(key in cfgDict for key in requiredKeys):
        return None
    return cfgDict
#############################################################################

if __name__ == '__main__':
    import pprint as pp
    import sys
    arguments  = sys.argv
    scriptName = arguments[0]
    userArgs   = arguments[1:]
    mnUut      = userArgs[0]
    print(scriptName)
    print(userArgs  )
    mnCfgDict = getCfgDict(mnUut)
    pp.pprint(mnCfgDict)
