# Raspberry Pi SIM800L GSM module

SIM800L GSM module library for the Raspberry Pi.

This library is a fork of https://github.com/jakhax/raspberry-pi-sim800l-gsm-module.

It allows sending, receiving and deleting SMS, as well as performing HTTP GET/POST requests and getting information from the module.

> SIM900/SIM800 are 2G only modems, make sure your provider supports 2G as it is already being phased out in a lot of areas around the world, else a 3G/4G modem like the SIM7100 / SIM5300 is warranted.  

##  Requirements
- Raspberry Pi with Raspbian Pi OS installed.
- Sim800L GSM module
- external power supply for the Sim800L (a capacitor and a diode might work)

## References
- [AT Datasheet](https://microchip.ua/simcom/2G/SIM800%20Series_AT%20Command%20Manual_V1.12.pdf)
- [Application notes](https://www.microchip.ua/simcom/?link=/2G/Application%20Notes)
- [Specifications](https://simcom.ee/documents/?dir=SIM800L)

Arduino:
- https://github.com/vshymanskyy/TinyGSM
- https://lastminuteengineers.com/sim800l-gsm-module-arduino-tutorial/


## Setup

### Hardware connection

![sim800l](https://user-images.githubusercontent.com/8292987/155906146-e6c934e1-34b1-4499-9efe-c497f54d88f3.jpg)

### Disable serial console
We will start by disabling serial console to enable communication between the pi and sim800l via serial0.

Open the terminal on your pi and run `sudo raspi-config` 
Select Interfaces → Serial 
Select No to the 1st prompt and Yes for the 2nd.

## API Documentation

#### `class SIM800L(port='/dev/serial0', baudrate=115000, timeout=3.0)`
- `port`: port name
- `baudrate`: baudrate in bps
- `timeout`: timeout in seconds

#### `check_sim()`
Check whether the SIM card has been inserted.
 *return*: True if the SIM is inserted, otherwise False

#### `command(cmdstr, lines=1, waitfor=500, msgtext=None)`
Executes an AT command
- `cmdstr`: AT command string
- `lines`: number of expexted lines
- `waitfor`: number of milliseconds to waith for the returned data
- `msgtext`: SMS text; to be used in case of SMS message command
 *return*: returned data (string)

#### `command_ok(cmd, check_download=False, check_error=False, cmd_timeout=10)`
Send AT command to the device and check that the return sting is OK
- `cmd`: AT command
- `check_download`: True if the “DOWNLOAD” return sting has to be checked
- `check_error`: True if the “ERROR” return sting has to be checked
- `cmd_timeout`: timeout in seconds
 *return*: True = OK received, False = OK not received. If check_error, can return “ERROR”; if check_download, can return “DOWNLOAD”

#### `connect_gprs(apn=None)`
Connect to the bearer and get the IP address of the PDP context.
Automatically perform the full PDP context setup.
Reuse the IP session if an IP address is found active.
- `apn`: APN name
 *return*: False if error, otherwise return the IP address (as string)

#### `delete_sms(index_id)`
Delete the SMS message referred to the index
- `index_id`: index in the SMS message list starting from 1
 *return*: None

#### `disconnect_gprs(apn=None)`
Disconnect the bearer.
 *return*: True if succesfull, False if error

#### `get_battery_voltage()`
Return the battery voltage in Volts
 *return*: floating (volts)

#### `get_ccid()`
Get the ICCID
 *return*: string

#### `get_date()`
Return the clock date available in the module
 *return*: datetime.datetime

#### `get_flash_id()`
Get the SIM800 GSM module flash ID
 *return*: string

#### `get_hw_revision()`
Get the SIM800 GSM module hw revision
 *return*: string

#### `get_imsi()`
Get the IMSI
 *return*: string

#### `get_ip()`
Get the IP address of the PDP context
 *return*: IP address string

#### `get_msgid()`
Return the unsolicited notification of incoming SMS
 *return*: number

#### `get_msisdn()`
Get the MSISDN subscriber number
 *return*:

#### `get_operator()`
Display the current network operator that the handset is currently
registered with.
 *return*: operator string

#### `get_operator_long()`
Display a full list of network operator names.
 *return*: string

#### `get_serial_number()`
Get the SIM800 GSM module serial number
 *return*: string

#### `get_service_provider()`
Get the Get Service Provider Name stored inside the SIM
 *return*: string

#### `get_signal_strength()`
Get the signal strength
 *return*: number; min = 3, max = 100

#### `get_temperature()`
Get the SIM800 GSM module temperature in Celsius degrees
 *return*: string

#### `get_unit_name()`
Get the SIM800 GSM module unit name
 *return*: string

#### `hard_reset(reset_gpio)`
Perform a hard reset of the SIM800 module through the RESET pin
- `reset_gpio`: RESET pin
 *return*: True if the SIM is active after the reset, otherwise False

#### `http(url=None, data=None, apn=None, method=None, http_timeout=10, keep_session=False)`
Run the HTTP GET method or the HTTP PUT method and return retrieved data
Automatically perform the full PDP context setup and close it at the end
(use keep_session=True to keep the IP session active). Reuse the IP
session if an IP address is found active.
Automatically open and close the HTTP session, resetting errors.
- `url`: URL
- `data`: input data used for the PUT method
- `apn`: APN name
- `method`: GET or PUT
- `http_timeout`: timeout in seconds
- `keep_session`: True to keep the PDP context active at the end
 *return*: False if error, otherwise the returned data (as string)

#### `internet_sync_time(time_server='193.204.114.232', time_zone_quarter=4, apn=None, http_timeout=10, keep_session=False)`
Connect to the bearer, get the IP address and sync the internal RTC with
the local time returned by the NTP time server (Network Time Protocol).
Automatically perform the full PDP context setup.
Disconnect the bearer at the end (unless keep_session = True)
Reuse the IP session if an IP address is found active.
- `time_server`: internet time server (IP address string)
- `time_zone_quarter`: time zone in quarter of hour
- `http_timeout`: timeout in seconds
- `keep_session`: True to keep the PDP context active at the end
 *return*: False if error, otherwise the returned date (datetime.datetime)

#### `is_registered()`
Check whether the SIM is Registered, home network
 *return*: Truse if registered, otherwise False

#### `read_and_delete_all()`
Read the first message
 *return*: text of the message

#### `read_next_message(all_msg=False)`
Read and delete messages.
Can be repeatedly called to read messages one by one and delete them.
- `all_msg`: True if no filter is used (read and non read messages).  Otherwise only the non read messages are returned.
 *return*: retrieved message text (string)

#### `read_sms(index_id)`
Read the SMS message referred to the index
- `index_id`: index in the SMS message list starting from 1
 *return*: None if error, otherwise return a tuple including: MSISDN origin number, SMS date string, SMS time string, SMS text

#### `send_sms(destno, msgtext)`
Send SMS message
- `destno`: MSISDN destination number
- `msgtext`: Text message
 *return*: ‘OK’ if message is sent, otherwise ‘ERROR’

#### `serial_port()`
Return the serial port (for direct debugging)
 *return*:

#### `set_date()`
Set the Linux system date with the GSM time
 *return*: date string

#### `setup()`
Run setup strings for the initial configuration of the SIM800 module

#### `sim800l.convert_gsm(string)`
Convert string to gsm03.38 bytes
- `string`: UTF8 string
 *return*: gsm03.38 bytes

#### `sim800l.convert_to_string(buf)`
Convert gsm03.38 bytes to string
- `buf`: gsm03.38 bytes
 *return*: UTF8 string

#### `check_incoming()`
Internal function.
Check incoming data from the module
 *return*: tuple

#### `get_clip()`
Not used

#### `set_charset_hex()`

#### `set_charset_ira()`

#### `callback_incoming(action)`

#### `callback_msg(action)`

#### `callback_no_carrier(action)`


## Usage examples

```python 
from sim800l import SIM800L
sim800l=SIM800L('/dev/serial0')
```

#### Return module information
```python
from sim800l import SIM800L

sim800l = SIM800L()
sim800l.setup()

print("Date:",
    sim800l.get_date())
print("Operator:",
    sim800l.get_operator())
print("Service provider:",
    sim800l.get_service_provider())
print("Signal strength:",
    sim800l.get_signal_strength(), "%")
print("Temperature:",
    sim800l.get_temperature(), "degrees")
print("MSISDN:",
    sim800l.get_msisdn())
print("Battery Voltage:",
    sim800l.get_battery_voltage(), "V")
print("IMSI:",
    sim800l.get_imsi())
print("ICCID:",
    sim800l.get_ccid())
print("Unit Name:",
    sim800l.get_unit_name())

if sim800l.is_registered():
    print("SIM is registered.")
else:
    print("SIM NOT registered.")
```

#### Sync time with internet
```python
sim800l.internet_sync_time(apn="...", time_zone_quarter=...)
```

#### Hard reset
```python
# connect the RST pin with GPIO23 (pin 16 of the Raspberry Pi)
sim800l.hard_reset(23)  # see schematics
```

#### Send SMS
```python
sms="Hello there"
#sim800l.send_sms(dest.no,sms)
sim800l.send_sms('2547xxxxxxxx',sms)
```

#### Read next SMS message
```python
msg = sim800l.read_next_message(all_msg=True)
```

#### HTTP GET samples
```python
print(sim800l.http("http://httpbin.org/ip", method="GET", apn="..."))
print(sim800l.http("http://httpbin.org/get", method="GET", apn="..."))
```

#### HTTP PUT sample
```python
print(sim800l.http("http://httpbin.org/post", data='{"name","abc"}', method="PUT", apn="..."))
```

#### Read n-th SMS
```python
id=...  # e.g., 1
sim800l.read_sms(id)
```

#### Callback action
```python
def print_delete():
    # Assuming the SIM has no SMS initially
    sms = sim800l.read_sms(1)
    print(sms)
    sim800l.delete_sms(1)

sim800l.callback_msg(print_delete)

while True:
    sim800l.check_incoming()
```
