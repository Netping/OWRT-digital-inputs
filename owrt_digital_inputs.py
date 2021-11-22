#!/usr/bin/python3
import ubus
import time
import random
import sys
import hashlib
from journal import journal
from threading import Thread
from threading import Lock
from owrt_snmp_protocol import snmp_protocol




module_name = 'DigitalInputs'
confName = 'diginsensorconf'
sensor_default = {}
sensors = []
threads = []
mutex = Lock()
snmp_pr = snmp_protocol()
max_sensors = 0


def calchash(fname):
    hash_md5 = hashlib.md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)

    return hash_md5.hexdigest()

def readhash(hashfile):
    value = ''
    with open(hashfile, "r") as f:
        value = f.readline()

    return value

def thread_poll(thread_id, sensor):
    while thread_id in threads:
        if sensor['template'] == 'SNMP':
            snmp_id = snmp_pr.get_snmp_value(sensor['snmp_addr'], sensor['community'], sensor['oid'], sensor['snmp_port'], sensor['timeout'])
            time.sleep(int(sensor['timeout']))
            value, err = snmp_pr.res_get_snmp_value(snmp_id)
                      
            mutex.acquire()

            sensor['status'] = err

            if value != '-1':
                sensor['state'] = value

            synchronize_config(sensor)

            mutex.release()
        else:
            journal.WriteLog(module_name, "Normal", "error", "thread_poll: Wrong template name " + sensor['template'])
                        
        time.sleep(sensor_default['period'])

def applyConf():
    confvalues = ubus.call("uci", "get", {"config": confName})
    for confdict in list(confvalues[0]['values'].values()):
        if confdict['.type'] == 'globals' and confdict['.name'] == 'globals':
            max_sensors = int(confdict['maxsensors'])
            continue

        if confdict['.type'] == 'sensor' and confdict['.name'] == 'prototype':
            sensor_default['name'] = confdict['name']
            sensor_default['description'] = confdict['description']
            sensor_default['ton_description'] = confdict['ton_desc']
            sensor_default['toff_description'] = confdict['toff_desc']
            sensor_default['template'] = confdict['template'] #maybe need map for this
            sensor_default['state'] = bool(int(confdict['state']))
            sensor_default['status'] = confdict['status']
            sensor_default['period'] = int(confdict['period'])
            continue

        if confdict['.type'] == 'sensor' and confdict['.name'] != 'prototype':
            sensor = {}
            sensor['name'] = sensor_default['name']

            #parse and fill new sensor
            try:
                sensor['section'] = confdict['.name']
            except:
                pass

            try:
                sensor['name'] = confdict['name']
            except:
                sensor['name'] = sensor_default['name']

            try:
                sensor['description'] = confdict['description']
            except:
                sensor['description'] = sensor_default['description']

            try:
                sensor['ton_description'] = confdict['ton_description']
            except:
                sensor['ton_description'] = sensor_default['ton_description']

            try:
                sensor['toff_description'] = confdict['toff_description']
            except:
                sensor['toff_description'] = sensor_default['toff_description']

            try:
                sensor['template'] = confdict['template'] #maybe need map for this
            except:
                sensor['template'] = sensor_default['template']

            try:
                sensor['state'] = bool(int(confdict['state']))
            except:
                sensor['state'] = bool(int(sensor_default['state']))

            try:
                sensor['status'] = confdict['status']
            except:
                sensor['status'] = sensor_default['status']

            try:
                sensor['period'] = int(confdict['period'])
            except:
                sensor['period'] = int(sensor_default['period'])

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

            if (len(sensors) < max_sensors):
                sensors.append(sensor)
            else:
                journal.WriteLog(module_name, "Normal", "error", "Too many sensors in config file")

            mutex.release()

    #update threads from sensors
    del threads[:]

    mutex.acquire()

    for s in sensors:
        thr_id = len(threads) + 1

        threads.append(thr_id)

        thr = Thread(target=thread_poll, args=(thr_id, s))
        thr.start()

    mutex.release()

def commit_handler():
    #reconfigure
    mutex.acquire()
    del sensors[:]
    mutex.release()

    applyConf()

def init():
    try:
        #ubus.connect()

        newHash = calchash("/etc/config/diginsensorconf")

        with open("/etc/netping_digital_inputs/diginsensor_hash", "w") as f:
            f.write(newHash)

        applyConf()

        #ubus.disconnect()
    except Exception as e:
        journal.WriteLog(module_name, "Normal", "error", "init: " + str(e))

def commit_poll():
    newHash = calchash("/etc/config/diginsensorconf")
    oldHash = readhash("/etc/netping_digital_inputs/diginsensor_hash")
    
    if newHash != oldHash:
        commit_handler()

        with open("/etc/netping_digital_inputs/diginsensor_hash", "w") as f:
            f.write(newHash)

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
    journal.WriteLog(module_name, "Normal", "notice", module_name + "started!")
    
    try:
        ubus.connect()

        init()

        #main implementation
        while(1):
            commit_poll()
            time.sleep(1)

    except KeyboardInterrupt:
        ubus.disconnect()
        del threads[:]

    journal.WriteLog(module_name, "Normal", "notice", module_name + "finished!")

if __name__ == '__main__':
    main()
