import machine
import ubinascii
from umqttsimple import MQTTClient
import time


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