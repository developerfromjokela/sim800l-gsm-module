#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###########################################################################
# Driver for SIM800L module (using AT commands)
# Running on Raspberry Pi
# Based on https://github.com/jakhax/raspberry-pi-sim800l-gsm-module with
# totally revised code and many enhancements.
###########################################################################

"""
- python3.7/python3.9 (tested with these versions)
sudo apt-get update
sudo apt-get -y upgrade
python3 -m pip install --upgrade pip
pip3 install pyserial
pip3 install gsm0338
"""

import os
import time
import sys
import traceback
import serial
import re
import logging
from datetime import datetime
import subprocess
from RPi import GPIO
import termios
import tty
import gsm0338


def convert_to_string(buf):
    """
    Convert gsm03.38 bytes to string
    :param buf: gsm03.38 bytes
    :return: UTF8 string
    """
    try:
        tt = buf.decode('gsm03.38').strip()
        return tt
    except UnicodeError:
        logging.debug("SIM800L - Unicode error: %s", buf)
        tmp = bytearray(buf)
        for i in range(len(tmp)):
            if tmp[i] > 127:
                tmp[i] = ord('#')
        return bytes(tmp).decode('gsm03.38').strip()


def convert_gsm(string):
    """
    Encode the string with 3GPP TS 23.038 / ETSI GSM 03.38 codec.
    :param string: UTF8 string
    :return: gsm03.38 bytes
    """
    return string.encode("gsm03.38")


class SIM800L:
    """
    Main class
    """

    def __init__(self, port="/dev/serial0", baudrate=115000, timeout=3.0):
        """
        SIM800L Class constructor
        :param port: port name
        :param baudrate: baudrate in bps
        :param timeout: timeout in seconds
        """
        self.ser = None
        try:
            self.ser = serial.Serial(
                port=port, baudrate=baudrate, timeout=timeout)
        except serial.SerialException as e:
            # traceback.print_exc(file = sys.stdout)
            # logging.debug(traceback.format_exc())
            logging.critical("SIM800L - Error opening GSM serial port - %s", e)
            return

        fd = self.ser.fileno()
        attr = termios.tcgetattr(fd)
        attr[3] &= ~termios.ECHO
        termios.tcsetattr(fd, termios.TCSANOW, attr)
        tty.setraw(fd)

        self.incoming_action = None
        self.no_carrier_action = None
        self.clip_action = None
        self._clip = None
        self.msg_action = None
        self._msgid = 0
        self.savbuf = None

    def check_sim(self):
        """
        Check whether the SIM card has been inserted.
        :return: True if the SIM is inserted, otherwise False
        """
        sim = self.command('AT+CSMINS?\n')
        return re.sub(r'\+CSMINS: \d*,(\d*).*', r'\1', sim) == '1'

    def get_date(self):
        """
        Return the clock date available in the module
        :return: datetime.datetime
        """
        date_string = self.command('AT+CCLK?\n')
        r = self.check_incoming()
        if r != ("OK", None):
            logging.error("SIM800L - wrong return message: %s", r)
        logging.debug("SIM800L - date_string: %s", date_string)
        date = re.sub(r'.*"(\d*/\d*/\d*,\d*:\d*:\d*).*', r"\1", date_string)
        logging.debug("SIM800L - date: %s", date)
        return datetime.strptime(date, '%y/%m/%d,%H:%M:%S')

    def is_registered(self):
        """
        Check whether the SIM is Registered, home network
        :return: Truse if registered, otherwise False
        """
        date_string = self.command('AT+CREG?\n')
        logging.debug("SIM800L - date_string: %s", date_string)
        registered = re.sub(r'^\+CREG: (\d*),(\d*)$', r"\2", date_string)
        if registered == "1" or registered == "5":
            return True
        return False

    def get_operator(self):
        """
        Display the current network operator that the handset is currently
        registered with.
        :return: operator string
        """
        operator_string = self.command('AT+COPS?\n')
        operator = re.sub(r'.*"(.*)".*', r'\1', operator_string).capitalize()
        if operator.startswith("+cops: 0"):
            raise ValueError("SIM Error")
        return operator

    # not useful
    def get_operator_long(self):
        """
        Display a full list of network operator names.
        :return: string
        """
        operator_string = self.command('AT+COPN\n')
        operator = re.sub(r'.*","(.*)".*', r'\1', operator_string)
        return operator

    def get_service_provider(self):
        """
        Get the Get Service Provider Name stored inside the SIM
        :return: string
        """
        sprov_string = self.command('AT+CSPN?\n')
        if sprov_string == "ERROR":
            raise ValueError("SIM Error")
        sprov = re.sub(r'.*"(.*)".*', r'\1', sprov_string)
        return sprov

    def get_battery_voltage(self):
        """
        Return the battery voltage in Volts
        :return: floating (volts)
        """
        battery_string = self.command('AT+CBC\n')
        battery = re.sub(r'\+CBC: \d*,\d*,(\d*)', r'\1', battery_string)
        return int(battery) / 1000

    def get_msisdn(self):
        """
        Get the MSISDN subscriber number
        :return:
        """
        msisdn_string = self.command('AT+CNUM\n')
        if msisdn_string == "OK":
            return "Unstored MSISDN"
        msisdn = re.sub(r'.*","([+0-9][0-9]*)",.*', r'\1', msisdn_string)
        return msisdn

    def get_signal_strength(self):
        """
        Get the signal strength
        :return: number; min = 3, max = 100
        """
        signal_string = self.command('AT+CSQ\n')
        signal = int(re.sub(r'\+CSQ: (\d*),.*', r'\1', signal_string))
        if signal == 99:
            return 0
        return (signal + 1) / 0.32  # min = 3, max = 100

    def get_unit_name(self):
        """
        Get the SIM800 GSM module unit name
        :return: string
        """
        return self.command('ATI\n')

    def get_hw_revision(self):
        """
        Get the SIM800 GSM module hw revision
        :return: string
        """
        return self.command('AT+CGMR\n')

    def get_serial_number(self):
        """
        Get the SIM800 GSM module serial number
        :return: string
        """
        return self.command('AT+CGSN\n')

    def get_ccid(self):
        """
        Get the ICCID
        :return: string
        """
        return self.command('AT+CCID\n')

    def get_imsi(self):
        """
        Get the IMSI
        :return: string
        """
        return self.command('AT+CIMI\n')

    def get_temperature(self):
        """
        Get the SIM800 GSM module temperature in Celsius degrees
        :return: string
        """
        temp_string = self.command('AT+CMTE?\n')
        temp = re.sub(r'\+CMTE: \d*,([0-9.]*).*', r'\1', temp_string)
        return temp

    def get_flash_id(self):
        """
        Get the SIM800 GSM module flash ID
        :return: string
        """
        return self.command('AT+CDEVICE?\n')

    def set_date(self):
        """
        Set the Linux system date with the GSM time
        :return: date string
        """
        date = self.get_date()
        date_string = date.strftime('%c')
        with subprocess.Popen(
                ["sudo", "date", "-s", date_string],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT) as sudodate:
            sudodate.communicate()
        return date

    def setup(self):
        """
        Run setup strings for the initial configuration of the SIM800 module
        """
        assert self.command('ATE0;+IFC=1,1\n') == 'OK'
        # ATE0        -> command echo off
        # AT+IFC=1,1  -> use XON/XOFF
        assert self.command(
            'AT+CLIP=1;+CMGF=1;+CLTS=1;+CSCLK=0;+CSCS="GSM";+CMGHEX=1\n') == 'OK'
        # AT+CLIP=1     -> caller line identification
        # AT+CMGF=1     -> plain text SMS
        # AT+CLTS=1     -> enable get local timestamp mode
        # AT+CSCLK=0    -> disable automatic sleep
        # AT+CSCS="GSM" -> Use GSM char set
        # AT+CMGHEX=1   -> Enable or Disable Sending Non-ASCII Character SMS

    def callback_incoming(self, action):
        self.incoming_action = action

    def callback_no_carrier(self, action):
        self.no_carrier_action = action

    def get_clip(self):
        """
        Not used
        """
        return self._clip

    def callback_msg(self, action):
        self.msg_action = action

    def get_msgid(self):
        """
        Return the unsolicited notification of incoming SMS
        :return: number
        """
        return self._msgid

    def set_charset_hex(self):
        """
        Set HEX character set (only hexadecimal values from 00 to FF)
        """    
        return self.command('AT+CSCS="HEX"\n')

    def set_charset_ira(self):
        """
        Set the International reference alphabet (ITU-T T.50) character set
        """
        return self.command('AT+CSCS="IRA"\n')

    def hard_reset(self, reset_gpio):
        """
        Perform a hard reset of the SIM800 module through the RESET pin
        :param reset_gpio: RESET pin
        :return: True if the SIM is active after the reset, otherwise False
        """
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(reset_gpio, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(reset_gpio, GPIO.HIGH)
        GPIO.output(reset_gpio, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(reset_gpio, GPIO.HIGH)
        time.sleep(7)
        return self.check_sim()

    def serial_port(self):
        """
        Return the serial port (for direct debugging)
        :return:
        """
        return self.ser

    def command(self,
            cmdstr, lines=1, waitfor=500, msgtext=None, flush_input=True):
        """
        Executes an AT command
        :param cmdstr: AT command string
        :param lines: number of expexted lines
        :param waitfor: number of milliseconds to waith for the returned data
        :param msgtext: SMS text; to be used in case of SMS message command
        :param flush_input: True if residual input is flushed before sending
            the command. False disables flushing.
        :return: returned data (string)
        """
        while self.ser.in_waiting and flush_input:
            flush = self.ser.readline()
            logging.debug("SIM800L - Flushing %s", flush)
        logging.debug(
            "SIM800L - Writing '%s'", cmdstr.replace("\n", "\\n").replace("\r", "\\r"))
        self.ser.write(convert_gsm(cmdstr))
        if lines == 0:
            return
        if msgtext:
            self.ser.write(convert_gsm(msgtext) + b'\x1A')
        if waitfor > 1000:  # this is kept from the original code...
            time.sleep((waitfor - 1000) / 1000)
        buf = self.ser.readline().strip()  # discard linefeed etc
        if lines == -1:
            if buf:
                buf = [buf] + self.ser.readlines()
            else:
                buf = self.ser.readlines()
            if not buf:
                return None
            result = ""
            for i in buf:
                result += convert_to_string(i) + "\n"
            return result
        if not buf:
            buf = self.ser.readline()
        if not buf:
            return None
        result = convert_to_string(buf)
        if lines > 1:
            self.savbuf = ''
            for i in range(lines - 1):
                buf = self.ser.readline()
                if not buf:
                    return result
                buf = convert_to_string(buf)
                if not buf == '' and not buf == 'OK' and not buf.startswith(
                        '+CMTI: "SM",'):
                    self.savbuf += buf + '\n'
        logging.debug("SIM800L - Returning '%s'", result)
        return result

    def send_sms(self, destno, msgtext):
        """
        Send SMS message
        :param destno: MSISDN destination number
        :param msgtext: Text message
        :return: 'OK' if message is sent, otherwise 'ERROR'
        """
        result = self.command('AT+CMGS="{}"\n'.format(destno),
                              lines=99,
                              waitfor=5000, # it means 4 seconds
                              msgtext=msgtext)
        if result and result == '>' and self.savbuf:
            params = self.savbuf.split(':')
            if params[0] == '+CUSD' or params[0] == '+CMGS':
                return 'OK'
        return 'ERROR'

    def read_sms(self, index_id):
        """
        Read the SMS message referred to the index
        :param index_id: index in the SMS message list starting from 1
        :return: None if error, otherwise return a tuple including:
                MSISDN origin number, SMS date string, SMS time string, SMS text
        """
        result = self.command('AT+CMGR={}\n'.format(index_id), lines=99)
        if result:
            params = result.split(',')
            if not params[0] == '':
                params2 = params[0].split(':')
                if params2[0] == '+CMGR':
                    number = params[1].replace('"', '').strip()
                    date = params[3].replace('"', '').strip()
                    msg_time = params[4].replace('"', '').strip()
                    return [number, date, msg_time, self.savbuf]
        return None

    def delete_sms(self, index_id):
        """
        Delete the SMS message referred to the index
        :param index_id: index in the SMS message list starting from 1
        :return: None
        """
        self.command('AT+CMGD={}\n'.format(index_id), lines=1)

    def command_ok(self,
                   cmd,
                   check_download=False,
                   check_error=False,
                   cmd_timeout=10):
        """
        Send AT command to the device and check that the return sting is OK
        :param cmd: AT command
        :param check_download: True if the "DOWNLOAD" return sting has to be
                                checked
        :param check_error: True if the "ERROR" return sting has to be checked
        :param cmd_timeout: timeout in seconds
        :return: True = OK received, False = OK not received. If check_error,
                    can return "ERROR"; if check_download, can return "DOWNLOAD"
        """
        logging.debug("SIM800L - Sending command '%s'", cmd)
        r = self.command(cmd + "\n")
        if r.strip() == "OK":
            return True
        if check_download and r.strip() == "DOWNLOAD":
            return "DOWNLOAD"
        if check_error and r.strip() == "ERROR":
            return "ERROR"
        if not r:
            expire = time.monotonic() + cmd_timeout
            s = self.check_incoming()
            while s[0] == 'GENERIC' and not s[1] and time.monotonic() < expire:
                time.sleep(0.1)
                s = self.check_incoming()
            if s == ("OK", None):
                return True
            if check_download and s == ("DOWNLOAD", None):
                return "DOWNLOAD"
            if check_error and s == ("ERROR", None):
                return "ERROR"
        logging.critical(
            "SIM800L - Missing 'OK' return message after: '%s': '%s'", cmd, r)
        return False

    def get_ip(self):
        """
        Get the IP address of the PDP context
        :return: IP address string
        """
        ip_address = None
        r = self.command('AT+SAPBR=2,1\n')
        s = self.check_incoming()
        if s != ("OK", None):
            logging.debug("SIM800L - Missing OK after SAPBR: %s", s)
            return False
        r1 = r.split(',')
        r2 = r1[0].split(':')
        ip_address0 = r1[2].replace('"', "")
        if r2[0].strip() == '+SAPBR' and r2[1].strip() == "1" and r1[1].strip() == "1":
            ip_address = ip_address0
        if ip_address0 == '0.0.0.0':
            logging.debug("SIM800L - NO IP Address: %s", ip_address0)
        return ip_address

    def disconnect_gprs(self, apn=None):
        """
        Disconnect the bearer.
        :return: True if succesfull, False if error
        """
        return self.command_ok('AT+SAPBR=0,1')

    def connect_gprs(self, apn=None):
        """
        Connect to the bearer and get the IP address of the PDP context.
        Automatically perform the full PDP context setup.
        Reuse the IP session if an IP address is found active.
        :param apn: APN name
        :return: False if error, otherwise return the IP address (as string)
        """
        if apn is None:
            logging.critical("Missing APN name")
            return False
        ip_address = self.get_ip()
        if ip_address is False:
            return False
        if ip_address:
            logging.info("SIM800L - Already connected: %s", ip_address)
        else:
            r = self.command_ok(
                'AT+SAPBR=3,1,"CONTYPE","GPRS";+SAPBR=3,1,"APN","' +
                apn + '";+SAPBR=1,1',
                check_error=True)
            if r == "ERROR":
                logging.critical("SIM800L - Cannot connect to GPRS")
                return False
            if not r:
                return False
            ip_address = self.get_ip()
            if not ip_address:
                logging.error("SIM800L - Missing IP Address")
                return False
            logging.debug("SIM800L - IP Address: %s", ip_address)
        return ip_address

    def internet_sync_time(self,
            time_server="193.204.114.232",  # INRiM NTP server
            time_zone_quarter=4,  # 1/4 = UTC+1
            apn=None,
            http_timeout=10,
            keep_session=False):
        """
        Connect to the bearer, get the IP address and sync the internal RTC with
        the local time returned by the NTP time server (Network Time Protocol).
        Automatically perform the full PDP context setup.
        Disconnect the bearer at the end (unless keep_session = True)
        Reuse the IP session if an IP address is found active.
        :param time_server: internet time server (IP address string)
        :param time_zone_quarter: time zone in quarter of hour
        :param http_timeout: timeout in seconds
        :param keep_session: True to keep the PDP context active at the end
        :return: False if error, otherwise the returned date (datetime.datetime)
        """
        ip_address = self.connect_gprs(apn=apn)
        if ip_address is False:
            if not keep_session:
                self.disconnect_gprs()
            return False
        cmd = 'AT+CNTP="' + time_server + '",' + str(time_zone_quarter)
        if not self.command_ok(cmd):
            logging.error("SIM800L - sync time did not return OK: %s", r)
        if not self.command_ok('AT+CNTP'):
            logging.error("SIM800L - AT+CNTP did not return OK.")
        expire = time.monotonic() + http_timeout
        s = self.check_incoming()
        while time.monotonic() < expire:
            if s[0] == 'GENERIC' and s[1] and s[1].startswith('+CNTP: '):
                break
            time.sleep(0.5)
            s = self.check_incoming()
        ret = False
        if not s or s[0] != 'GENERIC' or (s[0] == 'GENERIC' and s[1] and not s[1].startswith('+CNTP: ')):
            logging.error("SIM800L - Sync time generic error")
        elif s[1] == '+CNTP: 1':
            logging.debug("SIM800L - Network time sync successful")
            ret = self.get_date()
        else:
            if s[1] == '+CNTP: 61':
                    logging.error("SIM800L - Sync time network error")
            elif s[1] == '+CNTP: 62':
                logging.error("SIM800L - Sync time DNS resolution error")
            elif s[1] == '+CNTP: 63':
                logging.error("SIM800L - Sync time connection error")
            elif s[1] == '+CNTP: 64':
                logging.error("SIM800L - Sync time service response error")
            elif s[1] == '+CNTP: 65':
                logging.error("SIM800L - Sync time service response timeout")
        if not keep_session:
            self.disconnect_gprs()
        return ret

    def http(self,
             url=None,
             data=None,
             apn=None,
             method=None,
             http_timeout=10,
             keep_session=False):
        """
        Run the HTTP GET method or the HTTP PUT method and return retrieved data
        Automatically perform the full PDP context setup and close it at the end
        (use keep_session=True to keep the IP session active). Reuse the IP
        session if an IP address is found active.
        Automatically open and close the HTTP session, resetting errors.
        :param url: URL
        :param data: input data used for the PUT method
        :param apn: APN name
        :param method: GET or PUT
        :param http_timeout: timeout in seconds
        :param keep_session: True to keep the PDP context active at the end
        :return: False if error, otherwise the returned data (as string)
        """
        if url is None:
            logging.critical("Missing HTTP url")
            return False
        if method is None:
            logging.critical("Missing HTTP method")
            return False
        ip_address = self.connect_gprs(apn=apn)
        if ip_address is False:
            if not keep_session:
                self.disconnect_gprs()
            return False
        cmd = 'AT+HTTPINIT;+HTTPPARA="CID",1;+HTTPPARA="URL","' + url + '";+HTTPPARA="CONTENT","application/json"'
        if method == "GET":
            cmd = 'AT+HTTPINIT;+HTTPPARA="CID",1;+HTTPPARA="URL","' + url + '"'
        r = self.command_ok(cmd)
        if not r:
            self.command('AT+HTTPTERM\n')
            r = self.command_ok(cmd)
            if not r:
                if not keep_session:
                    self.disconnect_gprs()
                return False
        if method == "PUT":
            if not data:
                logging.critical("SIM800L - Null data paramether.")
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
            len_input = len(data)
            cmd = 'AT+HTTPDATA=' + str(len_input) + ',' + str(
                http_timeout * 1000)
            r = self.command_ok(cmd, check_download=True, check_error=True)
            if r == "ERROR":
                logging.critical("SIM800L - AT+HTTPDATA returned ERROR.")
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
            if r != "DOWNLOAD":
                logging.critical(
                    "SIM800L - Missing 'DOWNLOAD' return message: %s", r)
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
            logging.debug("SIM800L - Writing '%s'", data)
            self.ser.write((data + '\n').encode())
            expire = time.monotonic() + http_timeout
            s = self.check_incoming()
            while s == ('GENERIC', None) and time.monotonic() < expire:
                time.sleep(0.1)
                s = self.check_incoming()
            if s != ("OK", None):
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
            r = self.command_ok('AT+HTTPACTION=1')
            if not r:
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
        if method == "GET":
            r = self.command_ok('AT+HTTPACTION=0')
            if not r:
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
        expire = time.monotonic() + http_timeout
        s = self.check_incoming()
        while s[0] != 'HTTPACTION_' + method and time.monotonic() < expire:
            time.sleep(0.1)
            s = self.check_incoming()
        if s[0] != 'HTTPACTION_' + method:
            logging.critical(
                "SIM800L - Missing 'HTTPACTION' return message for '%s' method: %s", method, s)
            self.command('AT+HTTPTERM\n')
            if not keep_session:
                self.disconnect_gprs()
            return False
        len_read = s[1]
        r = self.command('AT+HTTPREAD\n')
        params = r.split(':')
        if len(params) == 2 and params[0] == '+HTTPREAD' and params[1].strip().isnumeric():
            lr = int(params[1].strip())
            if len_read != lr:
                logging.critical(
                    "SIM800L - Different number of read characters: %d != %d", len_read, lr)
                self.command('AT+HTTPTERM\n')
                if not keep_session:
                    self.disconnect_gprs()
                return False
        ret_data = ''
        expire = time.monotonic() + http_timeout
        while len(ret_data) < len_read and time.monotonic() < expire:
            ret_data += self.ser.read(len_read).decode(
                encoding='utf-8', errors='ignore')
        logging.debug(
            "Returned data: '%s'", ret_data.replace("\n", "\\n").replace("\r", "\\r"))
        r = self.check_incoming()
        if r != ("OK", None) and ret_data[-5:].strip() == 'OK':
            r = ("OK", None)
            ret_data = ret_data[:-6]
        if r != ("OK", None):
            logging.critical(
                "SIM800L - Missing 'OK' after reading characters: %s", r)
            self.command('AT+HTTPTERM\n')
            if not keep_session:
                self.disconnect_gprs()
            return False
        if len(ret_data) != len_read:
            logging.warning(
                "Length of returned data: %d. Expected: %d", len(ret_data), len_read)
        r = self.command_ok('AT+HTTPTERM')
        if not r:
            self.command('AT+HTTPTERM\n')
            if not keep_session:
                self.disconnect_gprs()
            return False
        if not keep_session:
            if not self.disconnect_gprs():
                self.command('AT+HTTPTERM\n')
                self.disconnect_gprs()
                return False
        return ret_data

    def check_incoming(self):
        """
        Check incoming data from the module
        :return: tuple
        """
        buf = None
        if self.ser.in_waiting:
            buf = self.ser.readline()
            buf = convert_to_string(buf)
            while buf.strip() == "" and self.ser.in_waiting:
                buf = self.ser.readline()
                buf = convert_to_string(buf)
            if not buf:
                return "GENERIC", buf
            logging.debug("SIM800L - read line: '%s'", buf)
            params = buf.split(',')

            if params[0][0:14] == "+HTTPACTION: 1":
                if params[1] != '200':
                    logging.critical("SIM800L - HTTPACTION_PUT return code: %s", buf)
                    return "HTTPACTION_PUT", False
                if not params[2].strip().isnumeric():
                    return "HTTPACTION_PUT", False
                return "HTTPACTION_PUT", int(params[2])

            elif params[0][0:14] == "+HTTPACTION: 0":
                if params[1] not in ('200', '301'):
                    logging.critical("SIM800L - HTTPACTION_GET return code: %s", buf)
                    return "HTTPACTION_GET", False
                if params[1] == '301':
                    logging.info("SIM800L - HTTPACTION_GET 301 Moved Permanently.")
                if not params[2].strip().isnumeric():
                    return "HTTPACTION_GET", False
                return "HTTPACTION_GET", int(params[2])

            elif params[0][0:5] == "+CMTI":
                self._msgid = int(params[1])
                if self.msg_action:
                    self.msg_action()
                return "CMTI", self._msgid

            elif params[0] == "NO CARRIER":
                self.no_carrier_action()
                return "NOCARRIER", None

            elif params[0] == "RING" or params[0][0:5] == "+CLIP":
                # @todo handle
                return "RING", None

            elif buf.strip() == "OK":
                return "OK", None

            elif buf.strip() == "DOWNLOAD":
                return "DOWNLOAD", None

        return "GENERIC", buf

    def read_and_delete_all(self, index_id=1):
        """
        Read the message at position 1, then delete all SMS messages, regardless
        the type (read, unread, sent, unsent, received)
        :return: text of the message
        """
        try:
            if id > 0:
                return self.read_sms(index_id)
        finally:
            self.command('AT+CMGDA="DEL ALL"\n', lines=1)

    def read_next_message(self, all_msg=False):
        """
        Read one message and then delete it.
        Can be repeatedly called to read messages one by one and delete them.
        :param all_msg: True if no filter is used (return both read and non read
                  messages). Otherwise, only the non read messages are returned.
        :return: retrieved message text (string)
        """
        if all_msg:
            rec = self.command('AT+CMGL="ALL",1\n')
        else:
            rec = self.command('AT+CMGL="REC UNREAD",1\n')
        if rec == "OK":
            return None
        index_s = re.sub(r'\+CMGL: (\d*),"STO.*', r'\1', rec)
        if index_s.isnumeric():
            logging.critical("SIM800L - Deleting message: %s", rec)
            self.delete_sms(int(index_s))
            return None
        try:
            index = int(re.sub(r'\+CMGL: (\d*),"REC.*', r'\1', rec))
            data = self.read_sms(index)
            self.delete_sms(index)
        except Exception:
            return None
        return data
