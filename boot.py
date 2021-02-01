import time
from machine import Pin
import machine
import os
from CONF import RESET_DEL_FILES, RESET_DELAY, RESET_BTN, RESET_LED


reset_led = Pin(RESET_LED,Pin.OUT)
reset_btn = Pin(RESET_BTN, Pin.IN, Pin.PULL_UP)


if not reset_btn.value():
    print('''GPIO %{pin} is closed !\nDevice will reset in a few seconds'''.format(pin = 14))

    for i in range(0,10):
        reset_led.value(1)
        time.sleep(RESET_DELAY)
        reset_led.value(0)
        time.sleep(RESET_DELAY)
        print('.', end='')
        if reset_btn.value():
            break

    for i in range(0,30):
        reset_led.value(1)
        time.sleep(RESET_DELAY/3)
        reset_led.value(0)
        time.sleep(RESET_DELAY/3)
        print('.', end='')
        if reset_btn.value():
            print('\n\nreset canceled\n\n')
            break

    if not reset_btn.value():
        print('reset the machine')
        for f in RESET_DEL_FILES:
            os.remove(f)
        machine.reset()

