# LED Tip Jar
# www.ledtipjar.com
# Fructus Design LLC 2020

import gc
import board
import busio as io
from digitalio import DigitalInOut, Direction, Pull
from analogio import AnalogIn
from time import sleep
import audioio
try:
    import audiocore
except ImportError:
    print("ERROR importing audiocore")
    audiocore = audioio
from random import randint
import adafruit_dotstar
from adafruit_espatcontrol import adafruit_espatcontrol
import adafruit_espatcontrol.adafruit_espatcontrol_socket as socket
import adafruit_requests as requests
# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise


''' New board adjusted to custom tip jar PCBA
['__class__', 'A1', 'A2', 'A3', 'D0', 'D1', 'D3',
'ESP8266_EN', 'ESP8266_GPIO0', 'ESP8266_GPIO2',
'ESP8266_RESET', 'EXP_GPIO1', 'EXP_GPIO2', 'I2C',
'MISO', 'MOSI', 'MOSI2', 'NEOPIXEL', 'RX', 'SCK',
'SCK2', 'SCL', 'SDA', 'SPEAKER', 'SPEAKER_ENABLE',
'SPI', 'TX', 'UART']
'''

'''
import board
dir(board)
'A1', 'A2', 'A3', 'A4', 'A5',
'ACCELEROMETER_INTERRUPT', 'ACCELEROMETER_SCL',
'ACCELEROMETER_SDA', 'D0', 'D1', 'D2', 'D3',
'D4', 'D5', 'D6', 'I2C', 'LEFT_BUTTON',
'MIDDLE_BUTTON', 'MISO', 'MOSI', 'NEOPIXEL',
'RIGHT_BUTTON', 'RX', 'SAOGPIO_1',
'SAOGPIO_2', 'SCK', 'SCL', 'SDA', 'SPEAKER',
'SPEAKER_ENABLE', 'SPI', 'STATUS_LED', 'TX', 'UART']
'''

wav_file_options=["cha-ching.wav", "apu_comeagain.wav"]

ir_sensor_wide = AnalogIn(board.A1)
ir_sensor_narrow = AnalogIn(board.A2)

ir_sensor_detect_threshold_wide = 3.0
ir_sensor_detect_threshold_narrow = 2.5

als = AnalogIn(board.A3)

tip_detected = False

# ESP8266 WIFI Setup
uart = io.UART(board.TX, board.RX, timeout=0.1)
resetpin = DigitalInOut(board.ESP8266_RESET)
#rtspin = DigitalInOut(board.ESP8266_GPIO0)
print("ESP AT commands")
esp = adafruit_espatcontrol.ESP_ATcontrol(uart, 115200,
          reset_pin=resetpin, debug=False)
print("Resetting ESP module")
esp.hard_reset()
requests.set_socket(socket,esp)

first_pass = True
while False:
    try:
        if first_pass :
            print("Scanning for AP's")
            for ap in esp.scan_APs():
                print(ap)
            print("Checking connection...")
            # secrets dictionary must contain 'ssid' and 'password' at a minimum
            print("Connecting...")
            esp.connect(secrets)
            print("Connected to AT software version ", esp.version)
            print("IP address ", esp.local_ip)
            first_pass = False
        print("Pinging 8.8.8.8...", end="")
        print(esp.ping("8.8.8.8"))
        #sleep(10)

    except (ValueError,RuntimeError, adafruit_espatcontrol.OKError) as e:
        print("Failed to get data, retrying\n", e)
        print("Resetting ESP module")
        esp.hard_reset()


amp_enable = DigitalInOut(board.SPEAKER_ENABLE)
amp_enable.direction = Direction.OUTPUT

## Audio setup
audio = audioio.AudioOut(board.SPEAKER)

# DotStar LED Setup
num_pixels = 4
pixels = adafruit_dotstar.DotStar(board.SCK, board.MOSI, num_pixels, brightness=0.1, auto_write=False)

# Color definitions
RED = (255, 0, 0)
YELLOW = (255, 150, 0)
ORANGE = (255, 40, 0)
GREEN = (0, 255, 0)
TEAL = (0, 255, 120)
CYAN = (0, 255, 255)
BLUE = (0, 0, 255)
PURPLE = (180, 0, 255)
MAGENTA = (255, 0, 20)
WHITE = (255, 255, 255)

## FUNCTIONS ##

def get_voltage(pin):
    return (pin.value * 3.3) / 65536

def check_tip_sensors():
    global ir_sensor_detect_threshold
    sensor_narrow = get_voltage(ir_sensor_narrow)
    sensor_wide = get_voltage(ir_sensor_wide)
    if (sensor_narrow > ir_sensor_detect_threshold_narrow) or (sensor_wide > ir_sensor_detect_threshold_wide):
        if sensor_narrow > ir_sensor_detect_threshold_narrow:
            print("NARROW DETECTED")
        if sensor_wide > ir_sensor_detect_threshold_wide:
            print("WIDE DETECTED")
        return True
    return False

def wheel(pos):
    # Input a value 0 to 255 to get a color value.
    # The colours are a transition r - g - b - back to r.
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

def color_fill(color, wait):
    pixels.fill(color)
    pixels.show()
    sleep(wait)


def rainbow_cycle(wait):
    global tip_detected
    for j in range(255):
        for i in range(num_pixels):
            rc_index = (i * 256 // num_pixels) + j
            pixels[i] = wheel(rc_index & 255)
            if check_tip_sensors():
                tip_detected = True
                return
        pixels.show()
        sleep(wait)

def tip_inserted_flash():
    for x in range(2):
        color_fill(RED, 0.1)
        color_fill(WHITE,0.1)
        color_fill(BLUE, 0.1)

def audio_test2():
    with audioio.AudioOut(board.SPEAKER) as audio:
        amp_enable.value = True
        #wavefile = audiocore.WaveFile(open("cha-ching.wav", "rb"))
        wave_file = open(wav_file_options[randint(0,len(wav_file_options)-1)], "rb")
        audio.play(wavefile)
        while audio.playing:
            pass
        amp_enable.value = False

def audio_test3():
    #with audioio.AudioOut(board.SPEAKER) as audio:
    amp_enable.value = True
    #wavefile = audiocore.WaveFile(open("cha-ching.wav", "rb"))
    wavefile = audiocore.WaveFile(open(wav_file_options[randint(0,len(wav_file_options)-1)], "rb"))
    audio.play(wavefile)
    while audio.playing:
        pass
    amp_enable.value = False

def play_audio():
    amp_enable.value = True
    wave_file = open(wav_file_options[randint(0,len(wav_file_options)-1)], "rb")
    wave = audioio.WaveFile(wave_file)
    tip_detected = False
    audio.play(wave)

def adjust_brightness():
    # 0.55V = Basement lights
    # 1.00V = Basement lights w/ hand 10cm over top
    # 1.50V = Basement lights w/ hand 2cm over top
    # 2.58V = Covered with finger
    als_val = get_voltage(als)
    if als_val < 0.55:
        pixels.brightness = 1.0
    elif als_val < 1.00:
        pixels.brightness = 0.8
    elif als_val < 1.50:
        pixels.brightness = 0.6
    elif als_val < 2.00:
        pixels.brightness = 0.4
    elif als_val < 2.40:
        pixels.brightness = 0.2
    else:
        pixels.brightness = 0.1

def get_url():
    URL = "http://wifitest.adafruit.com/testwifi/index.html"
    r = requests.get(URL)
    print("Status:", r.status_code)
    print("Content type:", r.headers['content-type'])
    print("Content size:", r.headers['content-length'])
    print("Encoding:", r.encoding)
    print("Text:", r.text)

# examples from https://learn.adafruit.com/circuitpython-essentials/circuitpython-dotstar
while False:

    for x in range(0,num_pixels-1):
        pixels[x] = RED
        pixels.show()
        sleep(1)

    # Change this number to change how long it stays on each solid color.
    color_fill(RED, 0.5)
    color_fill(YELLOW, 0.5)
    color_fill(ORANGE, 0.5)
    color_fill(GREEN, 0.5)
    color_fill(TEAL, 0.5)
    color_fill(CYAN, 0.5)
    color_fill(BLUE, 0.5)
    color_fill(PURPLE, 0.5)
    color_fill(MAGENTA, 0.5)
    color_fill(WHITE, 0.5)

    sleep(0.5)

    # Increase this number to slow down the rainbow animation.
    rainbow_cycle(0)

### MAIN CODE ###


# print("ESP AT GET URL")
# try:
    # get_url()
# except:
    # print("Failed to get URL contents")

print("ready to get tips")
while True:
    #print(ir_transistor.value)
    if check_tip_sensors() or tip_detected:
        print("cha-ching!")
        print("narrow: ",(get_voltage(ir_sensor_narrow),))
        print("wide: ",(get_voltage(ir_sensor_wide),))
        print("als: ",(get_voltage(als),))
        tip_inserted_flash()
        #play_audio_new()
        #play_audio()
        audio_test3()
        tip_detected = False
        #amp_enable.value = False
    else:
        if not audio.playing:
            amp_enable.value = False
        rainbow_cycle(0.05)
        #print("narrow: ",round(get_voltage(ir_sensor_narrow),2),"wide: ",round(get_voltage(ir_sensor_wide),2),)
        print("als: ",(get_voltage(als),))
        adjust_brightness()
    sleep(0.1)  # debounce delay