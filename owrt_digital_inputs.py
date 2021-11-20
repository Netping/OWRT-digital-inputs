#!/usr/bin/python3
import ubus
import time
import random
import sys
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
                sensor['section'] = confdict['.name']
            except:
                pass

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

                try:
                    sensor['timeout'] = confdict['timeout']
                except:
                    sensor['timeout'] = '0'

            mutex.acquire()

            sensors.append(sensor)

            mutex.release()

def commit_handler(event, data):
    #reconfigure
    if data['config'] == confName:
        del sensors[:]

        applyConf()

def init():
    try:
        #ubus.connect()

        applyConf()

        #ubus.disconnect()
    except Exception as e:
        journal.WriteLog(module_name, "Normal", "error", "init: " + str(e))

def main_poll():
    try:
        for sensor in sensors:
            mutex.acquire()
            s = sensor
            mutex.release()

                #polling by template
            if s['template'] == 'SNMP':
                snmp_id = snmp_pr.get_snmp_value(s['snmp_addr'], s['community'], s['oid'], s['snmp_port'], s['timeout'])
                time.sleep(int(s['timeout']))
                value, err = snmp_pr.res_get_snmp_value(snmp_id)
                        
                s['status'] = err

                if value != '-1':
                    s['state'] = value

                synchronize_config(s)
            else:
                journal.WriteLog(module_name, "Normal", "error", "main_poll: Wrong template name " + s['template'])
                        
            time.sleep(sensor_default['period'])
    except Exception as ex:
        journal.WriteLog(module_name, "Normal", "error", "main_poll: Exception error" + str(ex))

def poll():
    try:
        ubus.listen(("commit", commit_handler))
        ubus.loop(1)
    except Exception as e:
        journal.WriteLog(module_name, "Normal", "error", "poll: " + str(e))

def synchronize_config(sensor):
    try:
        state = ''
        status = ''
        updated = False

        confvalues = ubus.call("uci", "get", {"config": confName})
        for confdict in list(confvalues[0]['values'].values()):
            if confdict['.type'] == 'sensor' and confdict['.name'] == sensor['section']:
                state = confdict['state']
                status = confdict['status']

        if state != sensor['state']:
            ubus.call("uci", "set", {"config" : confName, "section" : sensor['section'], "values" : { "state" : sensor['state'] }})
            updated = True

        if status != sensor['status']:
            ubus.call("uci", "set", {"config" : confName, "section" : sensor['section'], "values" : { "status" : sensor['status'] }})
            updated = True

        if updated:
            #print('Sensor ' + sensor['name'] + ' changed')
            ubus.call("uci", "commit", {"config" : confName})
    except Exception as ex:
        journal.WriteLog(module_name, "Normal", "error", "synchronize_config: " + str(ex))

def main():
    #journal.WriteLog(module_name, "Normal", "notice", module_name + "started!")
    ubus.connect()

    init()

    #main implementation
    while(1):
        poll()
        main_poll()

    ubus.disconnect()

    #journal.WriteLog(module_name, "Normal", "notice", module_name + "finished!")

if __name__ == '__main__':
    main()
