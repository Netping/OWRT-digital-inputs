#!/usr/bin/python3
import ubus
import time
from journal import journal
from threading import Thread
from threading import Lock
from owrt_snmp_protocol import snmp_protocol




module_name = 'DigitalInputs'
confName = 'diginsensorconf'
sensor_default = {}
sensors = []
mutex = Lock()
snmp_pr = snmp_protocol()


def applyConf():
    confvalues = ubus.call("uci", "get", {"config": confName})
    for confdict in list(confvalues[0]['values'].values()):
        if confdict['.type'] == 'sensor' and confdict['.name'] == 'prototype':
            sensor_default['name'] = confdict['name']
            sensor_default['description'] = confdict['description']
            sensor_default['ton_description'] = confdict['ton_desc']
            sensor_default['toff_description'] = confdict['toff_desc']
            sensor_default['template'] = confdict['template'] #maybe need map for this
            sensor_default['state'] = bool(int(confdict['state']))
            sensor_default['status'] = confdict['status']
            sensor_default['period'] = int(confdict['period'])

        if confdict['.type'] == 'sensor' and confdict['.name'] != 'prototype':
            sensor = sensor_default

            #parse and fill new sensor
            try:
                sensor['name'] = confdict['name']
            except:
                pass

            try:
                sensor['description'] = confdict['description']
            except:
                pass

            try:
                sensor['ton_description'] = confdict['ton_description']
            except:
                pass

            try:
                sensor['toff_description'] = confdict['toff_description']
            except:
                pass

            try:
                sensor['template'] = confdict['template'] #maybe need map for this
            except:
                pass

            try:
                sensor['state'] = bool(int(confdict['state']))
            except:
                pass

            try:
                sensor['status'] = confdict['status']
            except:
                pass

            try:
                sensor['period'] = int(confdict['period'])
            except:
                pass

            if sensor['template'] == 'SNMP': #maybe need map for this
                try:
                    sensor['snmp_addr'] = confdict['snmp_addr']
                except:
                    sensor['snmp_addr'] = '0.0.0.0'

                try:
                    sensor['snmp_port'] = confdict['snmp_port']
                except:
                    sensor['snmp_port'] = '0'

                try:
                    sensor['community'] = confdict['community']
                except:
                    sensor['community'] = '0'

                try:
                    sensor['oid'] = confdict['oid']
                except:
                    sensor['oid'] = '0'

            mutex.acquire()

            sensors.append(sensor)

            mutex.release()

def commit_handler(event, data):
    #reconfigure
    if data['config'] == confName:
        del sensors[:]

        applyConf()

def ubus_init():
    try:
        ubus.connect()

        applyConf()

        ubus.disconnect()
    except Exception as e:
        print(e)
        journal.WriteLog(module_name, "Normal", "error", "ubus_init: Can't connect to ubus")

def register_handlers():
    try:
        ubus.connect()

        ubus.listen(("commit", commit_handler))
        ubus.loop()

        ubus.disconnect()
    except:
        journal.WriteLog(module_name, "Normal", "error", "register_handlers: Can't connect to ubus")

def synchronize_config(sensor):
    try:
        ubus.connect()

        #ubus.call("uci", "set", {"config" : confName, "section" : section, "values" : { option : value }}) #TODO how to update that value correctly?
        ubus.call("uci", "commit", {"config" : element['config']})        

        ubus.disconnect()
    except Exception as e:
        print(e)
        journal.WriteLog(module_name, "Normal", "error", "synchronize_config: Can't connect to ubus")

def poll():
    while (1): #TODO Ctrl+C condition handler
        for sensor in sensors:
            mutex.acquire()
            s = sensor
            mutex.release()

            #polling by template
            if s['template'] == 'SNMP':
                snmp_id = snmp_pr.get_snmp_value(s['snmp_addr'], s['community'], s['oid'], s['snmp_port'], s['period'])
                time.sleep(s['period'])
                value, err = snmp_pr.res_get_snmp_value(snmp_id)
                
                s['status'] = str(err)

                if value != -1:
                    s['state'] = str(value)

                #apply value and err for current sensor in config
                #synchronize_config(s)
            else:
                journal.WriteLog(module_name, "Normal", "error", "poll: Wrong template name " + s['template'])
                time.sleep(s['period'])

def main():
    #journal.WriteLog(module_name, "Normal", "notice", module_name + "started!")
    ubus_init()

    #main implementation
    thr = Thread(target=poll, args=())
    thr.start()

    register_handlers()
    #journal.WriteLog(module_name, "Normal", "notice", module_name + "finished!")

if __name__ == '__main__':
    main()
