import wifimgr
from wifimgr import send_header,handle_not_found
import BME280
import CCS811
from mqtt import MQTT
from CONF import (
    NETWORK_PROFILES, DEFAULT_HOST_IP, CONF_FILE, 
    DEFAULT_MQTT_SUB_TOPIC, DEFAULT_MQTT_PUB_TOPIC,
    PIN_SCL, PIN_SDA, SENSORS_SLEEP, SENSOR_FILE
    )
from time import sleep
import machine
from machine import ADC, Pin, I2C
import ure
try:
  import usocket as socket
except:
  import socket


##################################################################################
import _thread
import time
from umqttsimple import MQTTClient
import ubinascii
import micropython
import network
import esp
import os
esp.osdebug(None)
import gc
gc.collect()


wlan = wifimgr.get_connection()

i2c = I2C(scl=Pin(PIN_SCL), sda=Pin(PIN_SDA), freq=10000)

sensor_data = {}

if wlan is None:
    print("Could not initialize the network connection.")
    while True:
        machine.rest()

print("ESP OK")

def page_main(web_client, mqtt_connection):
    global sensor_data

    print(mqtt_connection)
    if mqtt_connection:
        mqtt_status = '5b5'
    elif not mqtt_connection:
        mqtt_status = 'd11'

    web_client.send('HTTP/1.1 200 OK\n')
    web_client.send('Content-Type: text/html\n')
    web_client.send('Connection: close\n\n')
    web_client.sendall("""\
        
        <html>
            <head> 
                <title>
                    ESP Web Server
                </title> 
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link rel="icon" href="data:,"> 
                <style>html{font-family: Helvetica; display:inline-block; margin: 0px auto;}
                h1{color: #0F3376; padding: 2vh;}.p{font-size: 1.5rem;}.button{display: inline-block; background-color: #e7bd3b; border: none; 
                border-radius: 4px; color: white; padding: 16px 40px; text-decoration: none; font-size: 30px; margin: 2px; cursor: pointer;}
                .button2{background-color: #4286f4;}.mqtt_dot{height: 10px;width: 10px;border-radius: 50%;display: inline-block}
                </style>
            </head>

            <body> 

                <h1>ESP Web Server</h1> 

                <tr align="left">
                    <td>MQTT Status: </td>
                    <td><span style="background-color: #"""+mqtt_status+""";" class="mqtt_dot"></span></td>
                </tr>
                <br>
                <br>
        """)
    for key in sensor_data:
        topic = key
        value = sensor_data.get(key)
        web_client.sendall("""\
                        <tr align="left">
                            <td>"""+str(key)+""": </td>
                            <td>"""+str(value)+"""</td>
                        </tr>
                        <br>
                        """)

    web_client.sendall("""\

                <form action="/configures" method="post">                
                    <p> <input type="submit" value="Einstellungen" /></p>
                </form>
                
            </body>

        </html>

        """)
    web_client.close()


def page_configures(web_client, config):
    wlan_sta = network.WLAN(network.STA_IF)
    wlan_sta.active(True)
    ssids = sorted(ssid.decode('utf-8') for ssid, *_ in wlan_sta.scan())

    web_client.send('HTTP/1.1 200 OK\n')
    web_client.send('Content-Type: text/html\n')
    web_client.send('Connection: close\n\n')
    web_client.sendall("""\
        <html>
            <head> 
                <title>
                    Configures
                </title> 
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <link rel="icon" href="data:,"> 
                <style>
                </style>
            </head>

            <body> 

                <h1>Configures</h1> 

                <form action="save_config" method="post">
                
                    <label for="fname">Host IP:</label>
                    <input type="text" id="host_ip" name="host_ip" value=""" + config.get('host_ip', DEFAULT_HOST_IP) + """ <br><br>

                    <h3>MQTT</h3> 
                    <label for="fname">Subscribe Topic:</label>
                    <input type="text" id="mqtt_sub_topic" name="mqtt_sub_topic" value=""" + config.get('mqtt_sub_topic', DEFAULT_MQTT_SUB_TOPIC) + """> <br><br>
                    <label for="fname">Publish Topic:</label>
                    <input type="text" id="mqtt_pub_topic" name="mqtt_pub_topic" value=""" + config.get('mqtt_pub_topic', DEFAULT_MQTT_PUB_TOPIC) + """> <br><br>

                
                    <p style="text-align: center;"> <input type="submit" value="Speichern" /></p>

                </form>

            </body>


    """)
    web_client.sendall("""\

            <h4 style="color: #5e9ca0; text-align: left;">
                <span style="color: #ff0000;">
                    Wi-Fi Client Setup
                </span>
            </h4>
            <form action="wifi_conf" method="post">
                <table style="margin-left: 0px; margin-right: auto;">
                    <tbody>
    """)
    while len(ssids):
        ssid = ssids.pop(0)
        web_client.sendall("""\
                        <tr>
                            <td colspan="2">
                                <input type="radio" name="ssid" value="{0}" />{0}
                            </td>
                        </tr>
        """.format(ssid))
    web_client.sendall("""\
                        <tr>
                            <td>Password:</td>
                            <td><input name="password" type="password" /></td>
                        </tr>
                    </tbody>
                </table>
                <p style="text-align: center;">
                    <input type="submit" value="Speichern" />
                </p>
            </form>

            <a style="text-align: center;" href="/main"> <button class="main_btn">Back</button> </a>

            <p>&nbsp;</p>
            <hr />
            <h5>
                <span style="color: #ff0000;">
                    Your ssid and password information will be saved into the
                    "%(filename)s" file in your ESP module for future usage.
                    Be careful about security!
                </span>
            </h5>
        </html>
    """ % dict(filename=NETWORK_PROFILES))

    web_client.close()

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


        sleep(SENSORS_SLEEP)



try: 
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('', 80))
    s.listen(5)
except OSError as e:
    print('Connection Error')



def check_msg(mqtt_client,mqtt):
    while True:
        mqtt_client.check_msg()
        topic, msg = mqtt.callback

        if msg != None and topic != None:
            topic, msg = mqtt.callback
            print(msg)

        mqtt.callback = None
        time.sleep(1)



config          = read_conf(CONF_FILE)
host_ip         = config.get('host_ip', DEFAULT_HOST_IP)
mqtt_sub_topic  = config.get('mqtt_sub_topic', DEFAULT_MQTT_SUB_TOPIC)
mqtt_pub_topic  = config.get('mqtt_pub_topic', DEFAULT_MQTT_PUB_TOPIC)


mqtt = MQTT(server=host_ip, sub_topic=mqtt_sub_topic, pub_topic=mqtt_pub_topic, callback=check_msg)
mqtt_client = mqtt.connect()
if mqtt_client:
    _thread.start_new_thread(check_msg, (mqtt_client,mqtt,))
    print('Connected to %s MQTT broker, subscribed to %s topic' % (mqtt.server, mqtt.sub_topic))

    _thread.start_new_thread(check_sensors, (mqtt,))








while True:
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

    elif response.get('method') == 'GET':

        if response.get('href') == '/configures':
            page_configures(web_client, config)

        elif response.get('href') == '/main' or response.get('href') == '/':
            page_main(web_client, mqtt.connection)



        elif response.get('href') == '/?led=off':
            print('LED OFF')
            mqtt.publish(config.get('mqtt_pub_topic',DEFAULT_MQTT_PUB_TOPIC), 'LED OFF')   #   Publish 

        elif response.get('href') == '/?led=on':
            print('LED ON')
            mqtt.publish(config.get('mqtt_pub_topic',DEFAULT_MQTT_PUB_TOPIC), 'LED ON')   #   Publish 

    page_main(web_client, mqtt.connection)

    
  except OSError as e:
    web_client.close()
    print('Connection closed' )


    