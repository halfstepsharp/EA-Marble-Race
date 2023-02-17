from machine import I2C, Pin, PWM, Timer
from time import sleep
from pico_i2c_lcd import I2cLcd
import rp2
import array
import _thread
import random
import gc
import os

#init. var.
barricade1, barricade2, barricade3 = [False] * 3 #false = closed
start_time = None
end_time = None
conveyorBeltPosition = "start"
carPosition = "end"

lcdfp_running = True
Stopwatch_running = True

servo1run = True
servo2run = True
servo3run = True
flag1 = True
flag2 = True
flag3 = True
resetflag = True
IR1flag = True
tflag1 = True
tflag2 = True
tflag3 = True #flag true means tgate can be changed

stopwatcht = Timer()
servo1on = Timer()
servo2on = Timer()
servo3on = Timer()
cbeltTimer = Timer()
stopbreset = Timer()
tgt1 = Timer()
tgt2 = Timer()
tgt3 = Timer()

s1 = 0
s10 = 0
m1 = 0
m10 = 0

#servo duty values
MIN = 2000000
MAX = 1000000
MID = int(MAX+((MIN-MAX)/2))
gMIN = 700000
gMID = int(MIN+((gMIN-MAX)/2))

lcdfp_running = True
Stopwatch_running = True
start3thread = False

#TODO: link buttons, servo, LEDs to GPIO pins
'''
3 pins for 3 RGB LEDs
2 pins for I2C LCD
3 target board servos
3 gate servos
3 target boards
'''
servo1 = PWM(Pin(3))
servo2 = PWM(Pin(2))
servo3 = PWM(Pin(1))
gate1servo = PWM(Pin(4))
gate2servo = PWM(Pin(5))
gate3servo = PWM(Pin(6))
tgtboard1 = Pin(9, Pin.IN, Pin.PULL_DOWN)		#active low
tgtboard2 = Pin(8, Pin.IN, Pin.PULL_DOWN)		#active low
tgtboard3 = Pin(7, Pin.IN, Pin.PULL_DOWN)		#active low
motordriverCW = Pin(10,Pin.OUT)
motordriverCCW = Pin(11,Pin.OUT)
startbutton = Pin(17, Pin.IN, Pin.PULL_UP) 		#active low
stopbutton 	= Pin(16, Pin.IN, Pin.PULL_UP) 		#active low
lswitch1 	= Pin(20, Pin.IN, Pin.PULL_DOWN)	#active low
IRmodule1 	= Pin(22, Pin.IN, Pin.PULL_DOWN)		#active low
IRmodule2 	= Pin(21, Pin.IN, Pin.PULL_DOWN)		#active low
ledRed 		= PWM(Pin(28))
ledRed.freq(1000)
ledBlue 	= PWM(Pin(27))
ledBlue.freq(1000)
ledGreen 	= PWM(Pin(26))
ledGreen.freq(1000)

servo1.freq(50)
servo2.freq(50)
servo3.freq(50)
gate1servo.freq(50)
gate2servo.freq(50)
gate3servo.freq(50)

# Create a button input on pin X
#button = machine.Pin(X, machine.Pin.IN, machine.Pin.PULL_UP)

#I2C, LCD
i2c = I2C(1, sda=Pin(14), scl=Pin(15), freq=400000) #I2C pins 14 &15
I2C_ADDR = i2c.scan()[0]
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16) #LCD
lcd.clear()
lcd.blink_cursor_on()
lcd.backlight_on()

ltdata_int = 0
hsdata_int = 0
ltdata = ""
hsdata = ""

#read lap time & high score from .txt
def readtimings():
    global lt, ltdata, hs, hsdata
    lt = open("lt.txt", "r")
    ltdata = lt.read()
    lt.close()
    hs = open("hs.txt", "r")
    hsdata = hs.read()
    hs.close()
    ltdata_int = int(ltdata.replace(':',''))
    hsdata_int = int(hsdata.replace(':',''))
    print("ltdata_int is " + str(ltdata_int) + ", hsdata_int is " + str(hsdata_int))
    
def ledr(val):
    brightness = int(65536*val)
    ledRed.duty_u16(brightness)
    
def ledb(val):
    brightness = int(65536*val)
    ledBlue.duty_u16(brightness)
    
def ledg(val):
    brightness = int(65536*val)
    ledGreen.duty_u16(brightness)

def rgbWhite():
    ledr(1)
    ledb(1)
    ledg(1)
    
def rgbYellow():
    ledr(1)
    ledb(0)
    ledg(1)
    
def rgbRed():
    ledr(1)
    ledb(0)
    ledg(0)
    
def rgbGreen():
    ledr(0)
    ledb(0)
    ledg(1)
    
def rgbBlack():
    ledr(0)
    ledb(0)
    ledg(0)

def rgbRand():
    ledr(random.random())
    ledb(random.random())
    ledg(random.random())
    
def randangle():
    global MIN
    global MAX
    i = int(MIN + (MAX - MIN) * random.random())
    #print("randangle = " + str(i))
    return i
   
def lcdfrontpageThread():
    global resetflag
    slptime = 2
    i = 0
    while lcdfp_running:
        lcd.clear()
        lcd.putstr("LapTime=  "+str(ltdata)+"\n")
        lcd.putstr("HighScore=" + str(hsdata))
        rgbRand()
        sleep(slptime)
        lcd.clear()
        lcd.putstr("Welcome, hold"+"\n")
        lcd.putstr("Start to begin")
        rgbRand()
        sleep(slptime)
        i+=1
        if (stopbutton.value() == 0):
            if (resetflag == True):
                stopbreset.init(period=10000, mode=machine.Timer.ONE_SHOT, callback=resethscallback)
                print("reset timer started")
                resetflag = False
        if i == 3:
            lcd.clear()
            lcd.putstr("Press stop to"+"\n")
            lcd.putstr("reset highscore")
            rgbRand()
            sleep(slptime)
            i = 0
    lcd.clear()
    lcd.putstr("Game is starting" + "\n")
    lcd.putstr("enjoy!")
    print("closing thread")
    gc.collect()
    _thread.exit()
    
def rand3servostimerThread():
    print("target board thread running")
    gc.collect()
    sleeptime = 2.5
    stopwatcht.init(period=1000, mode=machine.Timer.PERIODIC, callback=StpWatchIncrement)
    global servo1run, servo2run, servo3run, ltdata_int, hsdata_int, s1, s10, m1, m10
    while Stopwatch_running:
        print("stopwatch running")
        if servo1run:
            servo1.duty_ns(randangle())
        if servo2run:
            servo2.duty_ns(randangle())
        if servo3run:
            servo3.duty_ns(randangle())
        if s1 > 9:
            s10 += (s1 // 10)
            s1 %= 10
        if s10 > 5:
            m1 += (s10 // 6)
            s10 %= 6
        if m1 > 9:
            m10 += (m1 // 10)
            m1 %= 10
        if m10 > 5:
            m1 += (s10 // 6)
            s10 %= 6
        lcd.clear()
        lcd.putstr("timing = {}{}:{}{}".format(m10, m1, s10, s1))
        
        sleep(sleeptime)
        
        if (Stopwatch_running == False):
            break

    #once Stopwatch_running == False
    print("stopwatch_running false")
    if s1 > 9:
        s10 += (s1 // 10)
        s1 %= 10
    if s10 > 5:
        m1 += (s10 // 6)
        s10 %= 6
    if m1 > 9:
        m10 += (m1 // 10)
        m1 %= 10
    if m10 > 5:
        m1 += (s10 // 6)
        s10 %= 6
    lcd.clear()
    lcd.putstr("game complete! \nTime: " + "{}{}:{}{}".format(m10, m1, s10, s1))
    #write laptime
    f = open("lt.txt", "w")
    f.write("{}{}:{}{}".format(m10, m1, s10, s1))
    f.close()
    if ltdata_int < hsdata_int: #if laptime less than highscore
        hs = open("hs.txt", "w")
        hs.write("{}{}:{}{}".format(m10, m1, s10, s1))
        hs.close()
    stopwatcht.deinit()
    gc.collect()
    _thread.exit()
    
def StpWatchIncrement(self): 
    global s1
    s1 += 1

def resethscallback(self):
    global resetflag
    print("reset callback running")
    if (stopbutton.value() == 0):
        hs = open("hs.txt", "w")
        hs.write("59:59")
        hs.close()
        lcd.clear()
        readtimings()
        lcd.putstr("highscore has \nbeen reset")
        print ("reset done")
    else:
        print("reset unsuccessful")
    resetflag = True
    
def cbeltCallback(self):
    global motordriverCW, motordriverCCW
    motordriverCW.value(0)
    motordriverCCW.value(0)

def tgt1Callback(self):
    global tflag1, gate1servo
    tflag1 = True
    gate1servo.duty_ns(MIN)
    print("gate 1 closed")
    
def tgt2Callback(self):
    global tflag2, gate2servo
    tflag2 = True
    gate2servo.duty_ns(MIN)
    print("gate 2 closed")
    
def tgt3Callback(self):
    global tflag3, gate3servo
    tflag3 = True
    gate3servo.duty_ns(MIN)
    print("gate 3 closed")
    
def IRmodule1_irq(pin):
    global motordriverCW, motordriverCCW, IRflag1, start3thread, Stopwatch_running
    if (start3thread == False): 
        motordriverCW.value(0)
        motordriverCCW.value(0)
        print("motor stopped")
        flag3 = True
        start3thread = True
        Stopwatch_running = True
        print("start3thread = true" )
    
#display stats on screen
readtimings()
gate1 = 0
gate2 = 0
gate3 = 0

while True:
    #LED red
    rgbRed()
    gate1servo.duty_ns(MIN)
    gate2servo.duty_ns(MIN)
    gate3servo.duty_ns(MIN)

    Stopwatch_running = False
    lcdfp_running = True
    lcd.clear()
    lcd.putstr("welcome")
    servo1.duty_ns(MAX)
    servo2.duty_ns(MAX)
    servo3.duty_ns(MAX)
    gate1servo.duty_ns(MAX)
    gate2servo.duty_ns(MAX)
    gate3servo.duty_ns(MAX)
    sleep(2)
    servo1.duty_ns(MIN)
    servo2.duty_ns(MIN)
    servo3.duty_ns(MIN)
    gate1servo.duty_ns(MIN)
    gate2servo.duty_ns(gMIN)
    gate3servo.duty_ns(MIN)
    print("min")
    sleep(2)
    motordriverCW.value(0)
    motordriverCCW.value(0)
    if (lswitch1.value() == 1): #switch false
        lcd.clear()
        lcd.putstr("moving belt")
        print("moving belt 1")
        while (lswitch1.value() == 1):
            motordriverCW.value(1)
            if (lswitch1.value == 0):
                motordriverCW.value(0)
                break
    motordriverCW.value(0)

    print("starting landing screen")
    _thread.start_new_thread(lcdfrontpageThread, ()) #landing screen
    while startbutton.value():
        pass
    #once button pressed
    print("startbutton pressed")

    print("startbutton value is " + str(startbutton.value()))
    lcdfp_running = False
    sleep(3)

    #ConveyorBeltPosition to start
    motordriverCCW.value(1)
    print("moving belt 2")
    IRmodule1.irq(trigger=Pin.IRQ_FALLING, handler = IRmodule1_irq)
    while (Stopwatch_running == False):
        pass
        if (Stopwatch_running == True):
            break
        
    gate1servo.duty_ns(MIN)
    gate2servo.duty_ns(MIN)
    gate3servo.duty_ns(MIN)

    _thread.start_new_thread(rand3servostimerThread, ())
    lswitch1.irq(trigger=Pin.IRQ_RISING, handler = cbeltCallback)
    motordriverCW.value(1)
    while Stopwatch_running:
        if (tgtboard1.value() == 0):
            if (tflag1 == True):
                gate1servo.duty_ns(MAX)
                tflag1 = False
                print("gate 1 activated")
                gate1=1
                tgt1.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=tgt1Callback)
                
        if (tgtboard2.value() == 0):
            if (tflag2 == True):
                gate2servo.duty_ns(MAX)
                tflag2 = False
                print("gate 2 activated")
                gate2=1
                tgt2.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=tgt2Callback)
           
        if (tgtboard3.value() == 0):
            if (tflag3 == True):
                gate3servo.duty_ns(MAX)
                tflag3 = False
                print("gate 3 activated")
                gate3=1
                tgt3.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=tgt3Callback)
        if ((gate1 == 1) and (gate2 == 1) and (gate3 == 1)):
            sleep(3)
            Stopwatch_running = False
    tgt1.deinit()
    tgt2.deinit()
    tgt3.deinit()
    rgbWhite()
    sleep(1)
    rgbBlack()
    sleep(1)
    rgbRed()
    lcd.clear()
    lcd.putstr("YOU WIN! laptime:\n" + str(ltdata))
    for i in range(4):
        lcd.backlight_on()
        sleep(0.4)
        lcd.backlight_off()
        sleep(0.4)
    lcd.backlight_on()
    readtimings()
    start3thread = False
    print("game complete")
    sleep(3)
