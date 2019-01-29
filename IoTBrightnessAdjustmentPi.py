import RPi.GPIO as GPIO
import time
import sys
import serial
import logging
import microgear.client as microgear

gearkey = 'v9tAhW3u8FubX3X'
gearsecret = 'QiAHJtPxcNm4qRfWw0gQ14TdM'
appid = 'EmbeddedProject2'
this_name = 'RaspberryPi'


microgear.create(gearkey, gearsecret, appid, {'debugmode': True})


def connection():
    logging.info("Connected with Netpie")


def subscription(topic, message):
    global multi
    global DimStateChange
    global LightStateChange
    global red
    global green
    global blue
    global curtainAngle
    global Manual

    logging.info(topic + " " + message)
    if "/EmbeddedProject2/SetDimmer" in topic:
        multi = float(message) / 100.0
        DimStateChange = True
    elif "/EmbeddedProject2/SetRGBLED/" in topic:
        if "Red" in topic:
            red = int(message)
        elif "Green" in topic:
            green = int(message)
        elif "Blue" in topic:
            blue = int(message)
        LightStateChange = True
    elif "/EmbeddedProject2/SetCurtain" in topic:
        curtainAngle = int(message)
        if Manual:
            rotateCurtain(curtainAngle)


def disconnect():
    logging.debug("Disconnected")


microgear.setalias(this_name)
microgear.on_connect = connection
microgear.on_message = subscription
microgear.on_disconnect = disconnect
microgear.subscribe("/RGBLED/+")
microgear.subscribe("/SetRGBLED/+")
microgear.subscribe("/Dimmer")
microgear.subscribe("/SetDimmer")
microgear.subscribe("/Curtain")
microgear.subscribe("/SetCurtain")
# False means that the program will continue after connect with NetPie
microgear.connect(False)


GPIO.setmode(GPIO.BCM)

ser = serial.Serial('/dev/ttyACM0', 9600)
sys.stdout.flush()

servoPIN = 19
redPIN = 20
bluePIN = 21
greenPIN = 22
LDRthresholdL = 30


GPIO.setup(redPIN, GPIO.OUT)
GPIO.setup(greenPIN, GPIO.OUT)
GPIO.setup(bluePIN, GPIO.OUT)
GPIO.setup(servoPIN, GPIO.OUT)


p = GPIO.PWM(servoPIN, 50)  # GPIO 19 for PWM with 50Hz
p.start(2.5)  # Initialization

on = 100
off = 0
scale = 0.02

red = 100
green = 100
blue = 100
multi = 1.0

Freq = 100
RED = GPIO.PWM(redPIN, Freq)
GREEN = GPIO.PWM(greenPIN, Freq)
BLUE = GPIO.PWM(bluePIN, Freq)
LightON = False
Manual = False
LightStateChange = True
DimStateChange = True
curtainAngle = 0
read_serial = ""


def changeLightState(state):
    global LightStateChange
    if state == True:
        turnLightOn()
    else:
        turnLightOff()
    LightStateChange = False


def changeDimState():
    global DimStateChange
    global microgear
    if LightON:
        RED.start(int(red * multi))
        GREEN.start(int(green * multi))
        BLUE.start(int(blue * multi))
    if microgear.connected:
        microgear.publish("/Dimmer", multi)
    DimStateChange = False


def turnLightOff():
    global microgear
    RED.start(off)
    GREEN.start(off)
    BLUE.start(off)
    if microgear.connected:
        microgear.publish("/RGBLED/Red", 0)
        microgear.publish("/RGBLED/Green", 0)
        microgear.publish("/RGBLED/Blue", 0)


def turnLightOn():
    global microgear
    global red
    global green
    global blue
    RED.start(int(red * multi))
    GREEN.start(int(green * multi))
    BLUE.start(int(blue * multi))
    if microgear.connected:
        microgear.publish("/RGBLED/Red", red)
        microgear.publish("/RGBLED/Green", green)
        microgear.publish("/RGBLED/Blue", blue)


def rotateCurtain(angle):
    p.ChangeDutyCycle(2.5 + (angle/18))
    microgear.publish("/Curtain", angle)


try:
    while True:
        if ser.in_waiting:
            read_serial = ser.readline()
        if read_serial:
            read_serial = read_serial.rstrip()
            print("Serial message from Arduino: " + read_serial)

        if read_serial == "mode_manual":
            Manual = True
            rotateCurtain(0)
        elif read_serial == "mode_auto":
            Manual = False
            p.start(2.5)

        if Manual:
            if read_serial == "light_toggle":
                LightON = not LightON
                LightStateChange = True
                print("LightON = " + str(LightON))
        else:
            if "ldr_level" in read_serial:
                ldr = int(read_serial.split()[1])
                curtainAngle = 180 - (ldr // 5.69)
                if LDRthresholdL > ldr:
                    if not LightON:
                        LightON = True
                        LightStateChange = True
                    rotateCurtain(0)
                else:
                    if LightON:
                        LightON = False
                        LightStateChange = True
                    rotateCurtain(curtainAngle)

        if read_serial == "rotary CCW":
            multi = max(0.0, multi-scale)
            DimStateChange = True
        elif read_serial == "rotary CW":
            multi = min(1.0, multi+scale)
            DimStateChange = True

        if DimStateChange:
            changeDimState()
        if LightStateChange:
            changeLightState(LightON)
        read_serial = ""
        time.sleep(0.01)

except KeyboardInterrupt:
    p.stop()
    RED.stop()
    BLUE.stop()
    GREEN.stop()
    GPIO.cleanup()
