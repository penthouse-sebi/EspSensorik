import network
import socket
import ure
import time
import machine
import ubinascii
from umqttsimple import MQTTClient
try:
  import usocket as socket
except:
  import socket

from CONF import (
    HOTSPOT_SSID, HOTSPOT_PASSWORD, AUTHMODE, NETWORK_PROFILES
    )






class Wifi(object):

    server_socket = None
    wlan_ap = network.WLAN(network.AP_IF)
    wlan_sta = network.WLAN(network.STA_IF)

    def __connect(self, ssid, password):
        self.wlan_sta.active(True)
        if self.wlan_sta.isconnected():
            return None
        print('Trying to connect to %s...' % ssid)
        self.wlan_sta.connect(ssid, password)
        for retry in range(100):
            connected = self.wlan_sta.isconnected()
            if connected:
                break
            time.sleep(0.1)
            print('.', end='')
        if connected:
            print('\nConnected. Network config: ', self.wlan_sta.ifconfig())
        else:
            print('\nFailed. Not Connected to: ' + self.ssid)
        return connected

    def disconnect(self):
        self.wlan_sta.disconnect()
        if self.wlan_sta.isconnected():
            return True
        return False

    def isconnected(self):
        if self.wlan_sta.isconnected() and self.wlan_ap.isconnected():
            return True
        return False

    def read_profiles(self):
        with open(NETWORK_PROFILES) as f:
            lines = f.readlines()
        profiles = {}
        for line in lines:
            ssid, password = line.strip("\n").split(";")
            profiles[ssid] = password
        return profiles

    def write_profiles(self,profiles):
        lines = []
        for ssid, password in profiles.items():
            lines.append("%s;%s\n" % (ssid, password))
        with open(NETWORK_PROFILES, "w") as f:
            f.write(''.join(lines))

    def stop(self):

        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None

    def start_hotspot(self, port=80):

        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]

        self.stop()

        self.wlan_sta.active(True)
        self.wlan_ap.active(True)

        self.wlan_ap.config(essid=HOTSPOT_SSID, password=HOTSPOT_PASSWORD, authmode=AUTHMODE)

        self.server_socket = socket.socket()
        self.server_socket.bind(addr)
        self.server_socket.listen(1)

        print('Connect to WiFi ssid ' + HOTSPOT_SSID + ', default password: ' + HOTSPOT_PASSWORD)
        print('and access the ESP via your favorite web browser at 192.168.4.1.')
        print('Listening on:', addr)

        while True:
            if self.wlan_sta.isconnected():
                return True

            client, addr = self.server_socket.accept()
            print('client connected from', addr)
            try:
                client.settimeout(5.0)

                request = b""
                try:
                    while "\r\n\r\n" not in request:
                        request += client.recv(512)
                except OSError:
                    pass

                print("Request is: {}".format(request))
                if "HTTP" not in request:  # skip invalid requests
                    continue

                # version 1.9 compatibility
                try:
                    url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).decode("utf-8").rstrip("/")
                except Exception:
                    url = ure.search("(?:GET|POST) /(.*?)(?:\\?.*?)? HTTP", request).group(1).rstrip("/")
                print("URL is {}".format(url))

                if url == "":
                    self.handle_root(client)
                elif url == "wifi_conf":
                    self.handle_configure(client, request)
                else:
                    self.handle_not_found(client, url)

            finally:
                client.close()

    def get_connection(self):
        """return a working WLAN(STA_IF) instance or None"""

        # First check if there already is any connection:
        if self.wlan_sta.isconnected():
            return self.wlan_sta

        connected = False
        try:
            # ESP connecting to WiFi takes time, wait a bit and try again:
            time.sleep(3)
            if self.wlan_sta.isconnected():
                return self.wlan_sta

            # Read known network profiles from file
            profiles = self.read_profiles()

            # Search WiFis in range
            self.wlan_sta.active(True)
            networks = self.wlan_sta.scan()

            AUTHMODE = {0: "open", 1: "WEP", 2: "WPA-PSK", 3: "WPA2-PSK", 4: "WPA/WPA2-PSK"}
            for ssid, bssid, channel, rssi, authmode, hidden in sorted(networks, key=lambda x: x[3], reverse=True):
                ssid = ssid.decode('utf-8')
                encrypted = authmode > 0
                print("ssid: %s chan: %d rssi: %d authmode: %s" % (ssid, channel, rssi, AUTHMODE.get(authmode, '?')))
                if encrypted:
                    if ssid in profiles:
                        password = profiles[ssid]
                        connected = self.__connect(ssid, password)
                    else:
                        print("skipping unknown encrypted network")
                else:  # open
                    connected = self.__connect(ssid, None)
                if connected:
                    break

        except OSError as e:
            print("exception", str(e))

        # start web server for connection manager:
        if not connected:
            connected = self.start_hotspot()

        return self.wlan_sta if connected else None

    def handle_configure(self, client, request):
        match = ure.search("ssid=([^&]*)&password=(.*)", request)

        if match is None:
            self.send_response(client, "Parameters not found", status_code=400)
            return False
        # version 1.9 compatibility
        try:
            ssid = self.utf8_decode_replace(match.group(1)) #.decode("utf-8").replace("%3F", "?").replace("%21", "!").replace("+", " ")
            password = self.utf8_decode_replace(match.group(2)) #.decode("utf-8").replace("%3F", "?").replace("%21", "!").replace("%24", "$")


        except Exception:
            ssid = match.group(1).replace("%3F", "?").replace("%21", "!")
            password = match.group(2).replace("%3F", "?").replace("%21", "!")

        if len(ssid) == 0:
            self.send_response(client, "SSID must be provided", status_code=400)
            return False

        if self.__connect(ssid, password):
            response = """\
                <html>
                    <center>
                        <br><br>
                        <h1 style="color: #5e9ca0; text-align: center;">
                            <span style="color: #ff0000;">
                                ESP successfully connected to WiFi network %(ssid)s.
                            </span>
                        </h1>
                        <br><br>
                    </center>
                </html>
            """ % dict(ssid=ssid)
            self.send_response(client, response)
            try:
                profiles = self.read_profiles()
            except OSError:
                profiles = {}
            profiles[ssid] = password
            self.write_profiles(profiles)

            time.sleep(5)

            return True
        else:
            response = """\
                <html>
                    <center>
                        <h1 style="color: #5e9ca0; text-align: center;">
                            <span style="color: #ff0000;">
                                ESP could not connect to WiFi network %(ssid)s.
                            </span>
                        </h1>
                        <br><br>
                        <form>
                            <input type="button" value="Go back!" onclick="history.back()"></input>
                        </form>
                    </center>
                </html>
            """ % dict(ssid=ssid)
            self.send_response(client, response)
            return False

    def handle_root(self, client):
        self.wlan_sta.active(True)
        ssids = sorted(ssid.decode('utf-8') for ssid, *_ in self.wlan_sta.scan())
        self.send_header(client)
        client.sendall("""\
            <html>
                <h1 style="color: #5e9ca0; text-align: center;">
                    <span style="color: #ff0000;">
                        Wi-Fi Client Setup
                    </span>
                </h1>
                <form action="wifi_conf" method="post">
                    <table style="margin-left: auto; margin-right: auto;">
                        <tbody>
        """)
        while len(ssids):
            ssid = ssids.pop(0)
            client.sendall("""\
                            <tr>
                                <td colspan="2">
                                    <input type="radio" name="ssid" value="{0}" />{0}
                                </td>
                            </tr>
            """.format(ssid))
        client.sendall("""\
                            <tr>
                                <td>Password:</td>
                                <td><input name="password" type="password" /></td>
                            </tr>
                        </tbody>
                    </table>
                    <p style="text-align: center;">
                        <input type="submit" value="Submit" />
                    </p>
                </form>
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
        client.close()

    def handle_not_found(self, client, url):
        self.send_response(client, "Path not found: {}".format(url), status_code=404)

    def utf8_decode_replace(self, string):

        code_list = [["+", " "],["%20", " "],["%21", "!"],["%22", '"'],["%23", "#"],["%24", "$"],["%25", "%"],["%26", "&"]]
        string_utf = string.decode('utf-8')
        for code in code_list:
            string_utf = string_utf.replace(code[0],code[1])
        return(string_utf)

    def send_response(self, client, payload, status_code=200):
        content_length = len(payload)
        self.send_header(client, status_code, content_length)
        if content_length > 0:
            client.sendall(payload)
        client.close()

    def send_header(self, client, status_code=200, content_length=None ):
        client.sendall("HTTP/1.0 {} OK\r\n".format(status_code))
        client.sendall("Content-Type: text/html\r\n")
        if content_length is not None:
            client.sendall("Content-Length: {}\r\n".format(content_length))
        client.sendall("\r\n")



class MQTT(object):

    CLIENT_ID = ubinascii.hexlify(machine.unique_id())

    def __init__(self, callback, pub_topic, server='0.0.0.0', sub_topic='default'):
        self.__connection = False
        self.__server = server
        self.__sub_topic = sub_topic
        self.__callback = None
        self.__topic= None
        self.__msg= None

        if pub_topic[-1] != '/':
            pub_topic += '/'

        self.__pub_topic = pub_topic


    def connect(self):
        try:
            self.client = MQTTClient(self.CLIENT_ID, self.__server)
            self.client.set_callback(self.__sub_cb)
            self.client.connect()
            self.client.subscribe(self.__sub_topic)
            self.__connection = True
            return self.client
        except Exception:
            return None


    def publish(self, pub_topic, msg):
        self.client.publish(pub_topic, msg)


    def __sub_cb(self, topic, msg):
        self.__topic= topic.decode('utf-8')
        self.__msg= msg.decode('utf-8')



    @property
    def connection(self):
        return self.__connection

    @property
    def server(self):
        return self.__server

    @property
    def sub_topic(self):
        return self.__sub_topic


    @property
    def pub_topic(self):
        return self.__pub_topic


    @property
    def callback(self):
        return self.__topic, self.__msg


    @callback.setter
    def callback(self, msg):
        self.__topic= topic = msg
        self.__msg= msg = msg