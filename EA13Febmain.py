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

stopwatcht = Timer()
servo1on = Timer()
servo2on = Timer()
servo3on = Timer()
cbeltTimer = Timer()
stopbreset = Timer()

s1 = 0
s10 = 0
m1 = 0
m10 = 0

#servo duty values
MIN = 2500000
MAX = 250000
MID = int(MAX+((MIN-MAX)/2))
gMIN = 700000
gMID = int(MAX+((gMIN-MAX)/2))

lcdfp_running = True
Stopwatch_running = True
start3thread = False

#initializing pins
servo1 = PWM(Pin(1))
servo2 = PWM(Pin(2))
servo3 = PWM(Pin(3))
gate1servo = PWM(Pin(4))
gate2servo = PWM(Pin(5))
gate3servo = PWM(Pin(6))
tgtboard1 = Pin(7, Pin.IN, Pin.PULL_DOWN)		#active low
tgtboard2 = Pin(8, Pin.IN, Pin.PULL_DOWN)		#active low
tgtboard3 = Pin(9, Pin.IN, Pin.PULL_DOWN)		#active low
motordriverCW = Pin(10,Pin.OUT)
motordriverCCW = Pin(11,Pin.OUT)
startbutton = Pin(17, Pin.IN, Pin.PULL_UP) 		#active low
stopbutton 	= Pin(16, Pin.IN, Pin.PULL_UP) 		#active low
lswitch1 	= Pin(20, Pin.IN, Pin.PULL_DOWN)	#active low
IRmodule1 	= Pin(22, Pin.IN, Pin.PULL_UP)		#active low
IRmodule2 	= Pin(21, Pin.IN, Pin.PULL_UP)		#active low
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

#I2C LCD
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
    
#functions for setting LED color
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
#random LED color
def rgbRand():
    ledr(random.random())
    ledb(random.random())
    ledg(random.random())
#random angle for servos
def randangle():
    global MIN
    global MAX
    i = int(MIN + (MAX - MIN) * random.random())
    print("randangle = " + str(i))
    return i
#landing screen thread
def lcdfrontpageThread():
    global resetflag
    slptime = 2
    i = 0
    while lcdfp_running:
        lcd.clear() #clearing and setting I2C LCD display
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
        #hold red button to reset
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
#timer for LCD display and setting random angle on servos
def rand3servostimerThread():
    print("target board thread running")
    gc.collect()
    sleeptime = 3
    stopwatcht.init(period=1000, mode=machine.Timer.PERIODIC, callback=StpWatchIncrement)
    global servo1run, servo2run, servo3run, ltdata_int, hsdata_int, s1, s10, m1, m10
    while Stopwatch_running:
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
        #servo angles
        if servo1run:
            servo1.duty_ns(randangle())
        if servo2run:
            servo2.duty_ns(randangle())
        if servo3run:
            servo3.duty_ns(randangle())
        else: pass
    #once Stopwatch_running == False
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
    #closing thread
    stopwatcht.deinit()
    gc.collect()
    _thread.exit()
    
def StpWatchIncrement(self): 
    global s1
    s1 += 1
#resetting highscore
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
#reenabling servos
def servo1onCallback(self):
    gate1servo.duty_ns(MIN)
    global servo1run, flag1
    servo1run = True
    flag1 = True
    servo1on.deinit()
    
def servo2onCallback(self):
    gate2servo.duty_ns(MIN)
    global servo2run, flag2
    servo2run = True
    flag2 = True
    servo2on.deinit()
    
def servo3onCallback(self):
    gate3servo.duty_ns(MIN)
    global servo3run, flag3
    servo3run = True
    flag3 = True
    servo3on.deinit()
#stop conveyor
def cbeltCallback(self):
    global motordriverCW, motordriverCCW
    motordriverCW.value(0)
    motordriverCCW.value(0)
#interrupts for 
def tgt_irq1(pin):
    global servo1run, flag1
    if not servo1run:
        return
    servo1run = False
    flag1 = False

def tgt_irq2(pin):
    global servo2run, flag2
    if not servo2run:
        return
    servo2run = False
    flag2 = False

def tgt_irq3(pin):
    global servo3run, flag3
    if not servo3run:
        return
    servo3run = False
    flag3 = False
    
def IRmodule1_irq(pin):
    global motordriverCW, motordriverCCW, IRflag1, start3thread
    motordriverCW.value(0)
    motordriverCCW.value(0)
    print("motor stopped")
    flag3 = True
    start3thread = True
    print("start3thread = true" )
    
#display stats on screen
readtimings()

#LED red
rgbRed()

while True:
    Stopwatch_running = True
    lcdfp_running = True
    lcd.clear()
    lcd.putstr("welcome")
    for i in range(1):
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
    '''if (IRmodule1.value() == 1):
        while (IRmodule1.value() == 1):
            motordriverCCW.value(1)'''
    
    '''while (IRmodule1.value() == 1):
        pass
        if (IRmodule1.value() == 0):
            motordriverCCW.value(0)
            motordriverCW.value(0)
            break '''
    
    #once IRmodule1 detected, proceed
    #cbeltTimer.init(period=10000, mode=machine.Timer.ONE_SHOT, callback=cbeltCallback)
    #CarPosition to end
    #lap time to 0
    rgbRed()
        
    #Start game once conveyor belt is at top
    
    print("clearing memory")
    gc.collect()
    print("Free memory: ", gc.mem_free(), "bytes")
    print("checking target board values, starting interrupts")
    while (start3thread == False):
        pass
        print("start3thread = " + str(start3thread))
        sleep(0.1)
        if (start3thread == True):
            break
    _thread.start_new_thread(rand3servostimerThread, ())
    tgtboard1.irq(trigger=Pin.IRQ_RISING, handler = tgt_irq1)
    tgtboard2.irq(trigger=Pin.IRQ_RISING, handler = tgt_irq2)
    tgtboard3.irq(trigger=Pin.IRQ_RISING, handler = tgt_irq3)
    while Stopwatch_running:
        if servo1run == False:
            if not flag1: 
                print("tgt1 activated2")
                servo1.duty_ns(MID)
                gate1servo.duty_ns(MAX)
                servo1on.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=servo1onCallback)
                flag1 = True
        if servo2run == False:
            if not flag2:
                print("tgt2 activated2")
                servo2.duty_ns(MID)
                gate2servo.duty_ns(MAX)
                servo2on.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=servo2onCallback)
                flag2 = True
        if servo3run == False:
            print("servo3 false")
            if not flag3:
                print("tgt3 activated2")
                servo3.duty_ns(MID)
                gate3servo.duty_ns(MAX)
                print ("servos moved")
                servo3on.init(period=3000, mode=machine.Timer.ONE_SHOT, callback=servo3onCallback)
                print("timer started")
                flag3 = True
                print("flag set")
        IR2val = IRmodule2.value()
        if IR2val == False:
            Stopwatch_running = False
            print("IRmodule2 activated")
            #end game!
        sleep(0.1)
    servo1on.deinit()
    servo2on.deinit()
    servo3on.deinit()
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
