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
ubus_signals = []
mutex = Lock()
snmp_pr = snmp_protocol()
max_sensors = 0


def read_template(template):
    ret = {}

    confvalues = ubus.call("uci", "get", {"config": 'digintemplatesconf'})
    for confdict in list(confvalues[0]['values'].values()):
        if confdict['.type'] == 'info' and confdict['.name'] == template:
            ret = confdict
            del ret['.type']
            del ret['.name']
            del ret['.anonymous']
            del ret['.index']
            break

    return ret

def thread_poll(thread_id, sensor):
    while thread_id in threads:
        if sensor['template'] == 'SNMP':
            snmp_id = 0

            try:
                snmp_id = snmp_pr.get_snmp_value(sensor['snmp_addr'], sensor['community'], sensor['oid'], sensor['snmp_port'], sensor['timeout'])
            except:
                continue
                
            value, err = snmp_pr.res_get_snmp_value(snmp_id)
                          
            mutex.acquire()

            sensor['status'] = err
            send_name = sensor['name']

            if value != '-1':
                if value != sensor['state']:
                    e = {}
                    e['name'] = send_name
                    e['state'] = value

                    ubus_signals.insert(0, e)

                sensor['state'] = value
            
            mutex.release()

            time.sleep(sensor['period'])

        else:
            journal.WriteLog(module_name, "Normal", "error", "thread_poll: Wrong template name " + sensor['template'])

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
            sensor_default['template'] = confdict['protocol']
            sensor_default['state'] = '0'
            sensor_default['status'] = '0'
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
                sensor['ton_description'] = confdict['ton_desc']
            except:
                sensor['ton_description'] = sensor_default['ton_description']

            try:
                sensor['toff_description'] = confdict['toff_desc']
            except:
                sensor['toff_description'] = sensor_default['toff_description']

            try:
                sensor['template'] = confdict['protocol']
            except:
                sensor['template'] = sensor_default['template']

            try:
                sensor['period'] = int(confdict['period'])
            except:
                sensor['period'] = int(sensor_default['period'])

            sensor['state'] = sensor_default['state']
            sensor['status'] = sensor_default['status']

            if sensor['template'] == 'SNMP':
                template_sensor = read_template('SNMP')
                
                try:
                    sensor['snmp_addr'] = confdict['snmp_addr']
                except:
                    sensor['snmp_addr'] = template_sensor['snmp_addr']

                try:
                    sensor['snmp_port'] = confdict['snmp_port']
                except:
                    sensor['snmp_port'] = template_sensor['snmp_port']

                try:
                    sensor['community'] = confdict['community']
                except:
                    sensor['community'] = template_sensor['community']

                try:
                    sensor['oid'] = confdict['oid']
                except:
                    sensor['oid'] = template_sensor['oid']

                try:
                    sensor['timeout'] = confdict['timeout']
                except:
                    sensor['timeout'] = template_sensor['timeout']

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

def init():
    applyConf()

    def get_state_callback(event, data):
        ret_val = {}
        journal.WriteLog(module_name, "Normal", "notice", "get_state_callback called with data: " + str(data))
        sensor_name = data['name']

        found = False

        mutex.acquire()

        for s in sensors:
            if sensor_name == s['name']:
                ret_val['state'] = s['state']
                ret_val['status'] = s['status']
                found = True
                break

        mutex.release()

        if not found:
            ret_val['state'] = '-1'
            ret_val['status'] = '-2'

        event.reply(ret_val)

    ubus.add(
            'owrt_digital_inputs', {
                'get_state': {
                    'method': get_state_callback,
                    'signature': {
                        'name': ubus.BLOBMSG_TYPE_STRING,
                        'ubus_rpc_session': ubus.BLOBMSG_TYPE_STRING
                    }
                }
            }
        )

def reparseconfig(event, data):
    if data['config'] == confName:
        #reconfigure
        mutex.acquire()
        del sensors[:]
        mutex.release()

        applyConf()

def main():
    journal.WriteLog(module_name, "Normal", "notice", module_name + " started!")
    
    try:
        ubus.connect()

        init()

        ubus.listen(("commit", reparseconfig))

        while True:
            ubus.loop(1)
            while ubus_signals:
                e = ubus_signals.pop()
                ubus.send("signal", {"event": "statechanged", "name": e['name'], "state": e['state']})

    except KeyboardInterrupt:
        ubus.disconnect()
        del threads[:]

    journal.WriteLog(module_name, "Normal", "notice", module_name + " finished!")

if __name__ == '__main__':
    main()
