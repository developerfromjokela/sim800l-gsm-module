# EMULATOR! DO NOT COPY!
import logging
import time

class SIM800L:
    def setup(*args, **kwargs):
        print(f" - emulating SIM800L.setup")
    def get_date(*args, **kwargs):
        return time
    def set_date(*args, **kwargs):
        logging.debug(f" - emulating SIM800L.set_date pin = {args}")
        return time
    def send_sms(*args, **kwargs):
        logging.info(f" - emulating SIM800L.send_sms pin = {args}")
    def read_next_message(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.read_next_message pin = {args}")
        return None
    def get_operator(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_operator pin = {args}")
        return "operator"
    def get_service_provider(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_service_provider pin = {args}")
        return "service provider"
    def get_signal_strength(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_signal_strength pin = {args}")
        return 55
    def get_temperature(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_temperature pin = {args}")
        return "24.1"
    def get_msisdn(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_msisdn pin = {args}")
        return "+393355785665"
    def get_battery_voltage(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_battery_voltage pin = {args}")
        return "4.1"
    def get_imsi(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_imsi pin = {args}")
        return "imsi"
    def get_ccid(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_ccid pin = {args}")
        return "ccid"
    def get_unit_name(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_unit_name pin = {args}")
        return "unit name"
    def is_registered(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.is_registered pin = {args}")
        return True
    def serial_port(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.serial_port = {args}")
        return None
    def command(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.command = {args}")
        return ""
    def command_ok(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.command = {args}")
        return True
    def get_ip(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.get_ip = {args}")
        return "1.2.3.4"
    def http(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.http = {args}")
        return "http returned data"
    def check_incoming(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.check_incoming = {args}")
        return "GENERIC", None
    def read_and_delete_all(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.read_and_delete_all = {args}")
        return
    def delete_sms(*args, **kwargs):
        logging.verbose(f" - emulating SIM800L.delete_sms = {args}")
        return
    def set_charset_ira(self):
        return self.command('AT+CSCS="IRA"\n')
    def hard_reset(self, reset_gpio):
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(reset_gpio, GPIO.OUT, initial=GPIO.HIGH)
        GPIO.output(reset_gpio, GPIO.HIGH)
        GPIO.output(reset_gpio, GPIO.LOW)
        time.sleep(0.1)
        GPIO.output(reset_gpio, GPIO.HIGH)
        time.sleep(7)
        return self.check_sim()
    def convert_gsm(self, string):
        return string.encode("gsm03.38")
    def set_charset_hex(self):
        return self.command('AT+CSCS="HEX"\n')
    def check_sim(self):
        sim = self.command('AT+CSMINS?\n')
        return re.sub(r'\+CSMINS: \d*,(\d*).*', r'\1', sim) == '1'
