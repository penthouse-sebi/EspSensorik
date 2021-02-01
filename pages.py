import network
import ure
from CONF import NETWORK_PROFILES, DEFAULT_HOST_IP, DEFAULT_MQTT_SUB_TOPIC, DEFAULT_MQTT_PUB_TOPIC
import time



def page_main(web_client, mqtt_connection, sensor_data):

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

            <form action="upgrade" method="post">                
                <p style="text-align: center;"> <input type="submit" value="upgrade" /></p>
            </form>




        </html>
    """ % dict(filename=NETWORK_PROFILES))

    web_client.close()
