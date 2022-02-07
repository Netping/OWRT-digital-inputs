#!/usr/bin/python3
import os
import ubus

# for "test_config_params" function
configpath = '/etc/config/'
configname = 'diginsensorconf'
config_params_test = {
    'globals.globals': ['template.Empty', 'template.SNMP', 'status.0', 'status.1', 'status.2', 'maxsensors'],
    'sensor.prototype': ['name', 'description', 'ton_desc', 'toff_desc', 'template', 'state', 'status', 'period'],
    'sensor.anysensor': [
        'name', 'description', 'ton_desc', 'toff_desc', 'template', 'state', 'status', 'period',
        'snmp_addr', 'snmp_port', 'community', 'oid', 'timeout'
    ]
}
for k in config_params_test:
    config_params_test[k].sort()

ubus.connect()

def test_config_existance():
    ret = False
    try:
        if os.path.isfile(configpath + configname):
            ret = True
    except:
        assert ret
    assert ret

def test_config_params():
    ret = False
    print("\n")
    try:
        confvalues = ubus.call("uci", "get", {"config": configname})
        for confdict in list(confvalues[0]['values'].values()):
            cptkey = confdict['.type'] + '.' + confdict['.name']
            if confdict['.type'] == 'sensor' and cptkey not in config_params_test:
                cptkey = confdict['.type']  +  '.anysensor'
            if cptkey in config_params_test:
                config_params = {}
                config_params[confdict['.name']] = []
                for option in confdict:
                    if not option.startswith('.'):
                        tmpoptionlist = []
                        if isinstance(confdict[option], list):
                            for listoption in confdict[option]:
                                tmpoptionlist.append(option + '.' + listoption.split('.')[0])
                        else:
                            tmpoptionlist.append(option)
                        for tmpoption in tmpoptionlist:
                            if tmpoption in config_params_test[cptkey]:
                                config_params[confdict['.name']].append(tmpoption)
                            else:
                                print("---WARNING---: Unknown option \"" + option + "\" in section \"" + confdict['.type'] + "\" with name \"" + confdict['.name'] + "\" in config file")
                config_params[confdict['.name']].sort()
                assert config_params_test[cptkey] == config_params[confdict['.name']]
            else:
                print("---WARNING---: Unknown section \"" + confdict['.type']  + "\" with name \"" + confdict['.name'] + "\" in config file")
                continue
    except:
        assert ret

def test_ubus_get_state_method():
    ret = False
    try:
        res = ubus.call("owrt_digital_inputs", "get_state", {"name":"anyname", "ubus_rpc_session":""})
        if 'state' in res[0] and 'status' in res[0]:
            if res[0]['state'] in [str(x) for x in range(-1, 2)] and res[0]['status'] in [str(x) for x in range(-2, 3)]:
                ret = True
        assert ret
    except:
        assert ret
