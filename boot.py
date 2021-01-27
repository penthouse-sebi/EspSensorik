




import time
from machine import Pin
import machine
import os


RESET_DEL_FILES = ['wifi.dat']
timeout = 0.5
reset_led = Pin(16,Pin.OUT)
reset_btn = Pin(14, Pin.IN, Pin.PULL_UP)


if not reset_btn.value():
    print('''GPIO %{pin} is closed !\nDevice will reset in a few seconds'''.format(pin = 14))

    for i in range(0,10):
        reset_led.value(1)
        time.sleep(timeout)
        reset_led.value(0)
        time.sleep(timeout)
        print('.', end='')
        if reset_btn.value():
            break

    for i in range(0,30):
        reset_led.value(1)
        time.sleep(timeout/3)
        reset_led.value(0)
        time.sleep(timeout/3)
        print('.', end='')
        if reset_btn.value():
            print('\n\nreset canceled\n\n')
            break

    if not reset_btn.value():
        print('reset the machine')
        for f in RESET_DEL_FILES:
            os.remove(f)
        machine.reset()




# import ntptime
# import time

# #if needed, overwrite default time server
# ntptime.host = "1.europe.pool.ntp.org"

# try:
#   print("Local time before synchronization：%s" %str(time.localtime()))
#   #make sure to have internet connection
#   ntptime.settime()
#   print("Local time after synchronization：%s" %str(time.localtime()))
# except:
#   print("Error syncing time")