import time
import machine
from machine import ADC, Pin, I2C
import _thread
import esp
import ure
import os
import gc
try:
  import usocket as socket
except:
  import socket

import BME280
import CCS811

from upgrade import upgrade
from wifi import Wifi, MQTT
from pages import page_configures, page_main
from CONF import (
    NETWORK_PROFILES, DEFAULT_HOST_IP, CONF_FILE, 
    DEFAULT_MQTT_SUB_TOPIC, DEFAULT_MQTT_PUB_TOPIC,
    PIN_SCL, PIN_SDA, SENSORS_SLEEP, SENSOR_FILE
    )


esp.osdebug(None)
gc.collect()


# initialize the I2C Bus
i2c = I2C(scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=10000)
sensor_data = {}


# connect to WLAN. If no Wlan is reachable create Hotspot with Webinterface
wifi = Wifi()
wlan = wifi.get_connection()
if wlan is None:
    print("Could not initialize the network connection.")
    while True:
        machine.rest()




def read_conf(file_path):
    try:
        with open(file_path) as f:
            lines = f.readlines()
        c = {}
        for line in lines:
            key, value = line.strip("\n").split("=")
            c[key] = value
        return c
    except OSError as e:
        return {}

def write_conf(conf):
    lines = []
    for key, value in conf.items():
        lines.append("%s=%s\n" % (key, utf8_replace(value)))
    with open(CONF_FILE, "w") as f:
        f.write(''.join(lines))

def utf8_replace(string):
    code_list = [["+", " "],["%20", " "],["%21", "!"],["%22", '"'],["%23", "#"],["%24", "$"],["%25", "%"],["%26", "&"],["%2F", "/"]]
    for code in code_list:
        string = string.replace(code[0],code[1])
    return(string)

def check_msg(mqtt_client,mqtt):
    while wlan.isconnected():
        try:
            mqtt_client.check_msg()
            topic, msg = mqtt.callback

            if msg != None and topic != None:
                topic, msg = mqtt.callback
                print(msg)

            mqtt.callback = None
            time.sleep(1)
        except OSError:
            print('Error with MQTT')

def check_sensors(mqtt):
    global i2c, sensor_data

    bme = BME280.BME280(i2c=i2c)
    css = CCS811.CCS811(i2c=i2c, addr=90)

    while True:

        data = {} 
        data['temp'] = round(bme.temperature, 1)
        data['hum'] = round(bme.humidity, 1)
        data['pres'] = round(bme.pressure, 1)


        if css.data_ready():
            css.put_envdata(humidity=data['hum'],temp=data['temp'])
            data['eCO2'] = css.eCO2
            data['tVOC'] = css.tVOC


        for key in data:
            topic = key
            msg = data[key]
            mqtt.publish(mqtt.pub_topic + topic, str(msg) )


        sensor_data = data


        time.sleep(SENSORS_SLEEP)




# Get Config
config          = read_conf(CONF_FILE)
host_ip         = config.get('host_ip', DEFAULT_HOST_IP)
mqtt_sub_topic  = config.get('mqtt_sub_topic', DEFAULT_MQTT_SUB_TOPIC)
mqtt_pub_topic  = config.get('mqtt_pub_topic', DEFAULT_MQTT_PUB_TOPIC)


# Connect to MQTT Broker
mqtt = MQTT(server=host_ip, sub_topic=mqtt_sub_topic, pub_topic=mqtt_pub_topic, callback=check_msg)
mqtt_client = mqtt.connect()

# 
if mqtt_client:
    # Start listening to MQTT Topic
    _thread.start_new_thread(check_msg, (mqtt_client,mqtt,))

    print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt.server, mqtt.sub_topic))

    _thread.start_new_thread(check_sensors, (mqtt,))


try: 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
except OSError as e:
    print('Connection Error')



while wlan.isconnected():
  try:
    if gc.mem_free() < 102000:
      gc.collect()
    web_client, addr = s.accept()
    web_client.settimeout(3.0)
    print('Got a connection from %s' % str(addr))
    request = web_client.recv(1024)
    web_client.settimeout(None)
    request = request.decode('utf-8')
    request = str(request)


    r = request.splitlines()
    response = {}
    if r != []:
        response['method'] = r[0].split(' ')[0]
        response['href'] = r[0].split(' ')[1]
        response['data'] = r[-1].split('&')

        for line in request.splitlines():
            l = line.split(': ')
            if len(l) == 2:
                response[l[0].lower()] = l[1]

       # Debug
        # print(response.get('method'))
        # print(response.get('data'))
        # print(response.get('href'))
        # print(response.get('referer'))


    if response.get('method') == 'POST':
        if response.get('href') == '/configures':
            page_configures(web_client, config)

        if response.get('href') == '/save_config':
            print('Save configures')
            c = {}
            for line in request.splitlines()[-1].split('&'):
                key, value = line.strip("\n").split("=")
                c[key] = value
            write_conf(c)
            page_configures(web_client, config)

        # if response.get('href') == '/upgrade':
        #     print('Upgrade....')
        #     upgrade()

        if response.get('href') == '/wifi_conf':

            ssid = utf8_replace(response['data'][0].split('=')[1])
            password = utf8_replace(response['data'][1].split('=')[1])

            try:
                profiles = wifi.read_profiles()
            except OSError:
                profiles = {}
            profiles[ssid] = password
            wifi.write_profiles(profiles)





    elif response.get('method') == 'GET':

        if response.get('href') == '/configures':
            page_configures(web_client, config)

        elif response.get('href') == '/main' or response.get('href') == '/':
            page_main(web_client, mqtt.connection, sensor_data)



        elif response.get('href') == '/?led=off':
            print('LED OFF')
            mqtt.publish(config.get('mqtt_pub_topic',DEFAULT_MQTT_PUB_TOPIC), 'LED OFF')   #   Publish 

        elif response.get('href') == '/?led=on':
            print('LED ON')
            mqtt.publish(config.get('mqtt_pub_topic',DEFAULT_MQTT_PUB_TOPIC), 'LED ON')   #   Publish 

    page_main(web_client, mqtt.connection, sensor_data)

    
  except OSError as e:
    web_client.close()
    print('Connection closed' )