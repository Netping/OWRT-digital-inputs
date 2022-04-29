#!/usr/bin/python3
import ubus
import os
import time

# config info
config = "diginsensorconf"
config_path = "/etc/config/"

# ubus methods info
test_ubus_objects = [
    {
        'uobj': 'owrt_digital_inputs',
        'umethods': [
            {
                'umethod': 'get_state',
                'inparams': {"name":"Door1", "ubus_rpc_session":""},
                'outparams': {
                    'state': ["__contains__", [str(x) for x in range(-1,2)]],
                    'status': ["__contains__", [str(x) for x in range(-2,3)]]
                }
            },
        ]
    },
]

try:
    ubus.connect()
except:
    print("Can't connect to ubus")

def test_conf_existance():
    ret = False

    try:
        ret = os.path.isfile(f"{config_path}{config}")
    except:
        assert ret

    assert ret

def test_conf_valid():
    ret = False

    try:
        # ubus.connect()
        confvalues = ubus.call("uci", "get", {"config": config})
        for confdict in list(confvalues[0]['values'].values()):
            #check globals
            if confdict['.type'] == 'globals' and confdict['.name'] == 'globals':
                assert confdict['protocol'] == ['Empty.пусто', 'SNMP.датчик устройства NetPing по SNMP']
                assert confdict['status'] == ['0.Normal', '1.Timeout', '2.Error']
                assert confdict['maxsensors'] == '32'
            #check sensor_prototype
            if confdict['.type'] == 'sensor' and confdict['.name'] == 'prototype':
                assert confdict['name'] == 'SensorName'
                assert confdict['description'] == 'Description'
                assert confdict['ton_desc'] == 'ON'
                assert confdict['toff_desc'] == 'OFF'
                assert confdict['protocol'] == 'Empty'
                assert confdict['period'] == '1'
    except:
        assert ret

def test_ubus_methods_existance():
    ret = False

    try:
        test_uobj_list = [x['uobj'] for x in test_ubus_objects]
        test_uobj_list.sort()
        uobj_list = []
        for l in list(ubus.objects().keys()):
            if l in test_uobj_list:
                uobj_list.append(l)
        uobj_list.sort()
        assert test_uobj_list == uobj_list
    except:
        assert ret

def test_ubus_api():
    ret = False

    try:
        #set config items
        testsensor = 'testsensor'
        if os.system(f"uci set {config}.{testsensor}=sensor"):
            raise ValueError("Can't create new section")

        if os.system(f"uci set {config}.{testsensor}.name='Door2'"):
            raise ValueError("Can't set option memo")

        if os.system(f"uci set {config}.{testsensor}.description='Дверь шкафа'"):
            raise ValueError("Can't set option unit")

        if os.system(f"uci set {config}.{testsensor}.ton_desc='Дверь открыта'"):
            raise ValueError("Can't set option precision")

        if os.system(f"uci set {config}.{testsensor}.toff_desc='Дверь закрыта'"):
            raise ValueError("Can't set option proto")

        if os.system(f"uci set {config}.{testsensor}.template='SNMP'"):
            raise ValueError("Can't set option community")

        if os.system(f"uci set {config}.{testsensor}.state='0'"):
            raise ValueError("Can't set option address")

        if os.system(f"uci set {config}.{testsensor}.status='0'"):
            raise ValueError("Can't set option oid")

        if os.system(f"uci set {config}.{testsensor}.snmp_addr='125.227.188.172'"):
            raise ValueError("Can't set option type_oid")

        if os.system(f"uci set {config}.{testsensor}.snmp_port='31161'"):
            raise ValueError("Can't set option port")

        if os.system(f"uci set {config}.{testsensor}.community='SWITCH'"):
            raise ValueError("Can't set option timeout")

        if os.system(f"uci set {config}.{testsensor}.oid='.1.3.6.1.4.1.25728.5500.5.1.2.1'"):
            raise ValueError("Can't set option period")

        if os.system(f"uci set {config}.{testsensor}.timeout='3'"):
            raise ValueError("Can't set option period")

        if os.system(f"uci set {config}.{testsensor}.period='1'"):
            raise ValueError("Can't set option period")

        if os.system(f"uci commit {config}"):
            raise ValueError("Can't commit config {config}")

        #send commit signal for module
        if os.system("ubus send commit '{\"config\":\"" + config + "\"}'"):
            raise ValueError("Can't send commit signal to {config}")

        #wait for sensor getting value
        time.sleep(5)
    except:
        assert ret

    try:
        test_uobjs = [x for x in test_ubus_objects]
        for uobj in test_uobjs:
            test_uobj_methods = [x for x in uobj['umethods']]
            for method in test_uobj_methods:
                res = ubus.call(uobj['uobj'], method['umethod'], method['inparams'])
                assert type(method['outparams']) == type(res[0])
                if isinstance(method['outparams'], dict):
                    for key in method['outparams']:
                        assert key in res[0]
                        if key in res[0]:
                            assert getattr(method['outparams'][key][1], method['outparams'][key][0])(res[0][key])
    except:
        assert ret
        
    #delete section from config
    os.system(f"uci delete {config}.{testsensor}")
    os.system(f"uci commit {config}")
    os.system("ubus send commit '{\"config\":\"" + config + "\"}'")
