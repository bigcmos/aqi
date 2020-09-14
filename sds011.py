# ESP32 - https://www.hackster.io/taunoerik/using-sds011-dust-sensor-01f019
# RASPBERRY PI - https://www.raspberrypi.org/blog/monitor-air-quality-with-a-raspberry-pi/
import serial, time
from datetime import datetime, timezone

ser = serial.Serial('/dev/ttyUSB0')


# Data Sheet for SDS011
# https://cdn-reichelt.de/documents/datenblatt/X200/SDS011-DATASHEET.pdf
#
# Bit rate: 9600
# Data bit: 8
# Parity bit: NO
# Stop bit: 1
#
# Data Packet freqency: 1Hz
#
# _________________________________________________________
# |   byte #   |   Name             |    Content          |
# |____________|____________________|_____________________|
# |        0   |   Message Header   |   AA                |
# |        1   |   Commander No.    |   C0                |
# |        2   |   DATA 1           |   PM2.5 Low Byte    |
# |        3   |   DATA 2           |   PM2.5 High Byte   |
# |        4   |   DATA 3           |   PM10 Low Byte     |
# |        5   |   DATA 4           |   PM10 High Byte    |
# |        6   |   DATA 5           |   ID Byte 1         |
# |        7   |   DATA 6           |   ID Byte 2         |
# |        8   |   Check-sum        |   Checksum          |
# |        9   |   Message Tail     |   AB                |
# |____________|____________________|_____________________|
#
# Checksum=DATA1+DATA2+...+DATA6
#
# PM2.5 (ug/m^3) = ((PM2.5 High Byte) << 8 + PM2.5 Low Byte) / 10
# PM10 (ug/m^3) = ((PM10 High Byte) << 8 + PM10 Low Byte) / 10


# AQI PM2.5
# 0 to 12.0    GOOD 0 to 50   Little
#
# https://blissair.com/what-is-pm-2-5.htm
class AQI:
    class Data:
        def __init__(self, pm2_5, aqi_thresh, aqi_name, aqi_color, health_effects, actions):
            self.pm2_5 = pm2_5
            self.aqi_thresh = aqi_thresh
            self.aqi_name = aqi_name
            self.aqi_color = aqi_color
            self.health_effects = health_effects
            self.actions = actions


    AQI_TABLE = [
        Data(0.0,   0,   "OFF_CHARTS",                     "-",           "-",                  "-"),
        Data(12.0,  50,  "Good",                           "GREEN",       "Little to no risk.", "None."),
        Data(35.4,  100, "Moderate",                       "YELLOW",      "TBD.", "TBD."),
        Data(55.4,  150, "Unhealthy for Sensative Groups", "ORANGE",      "TBD.", "TBD."),
        Data(150.4, 200, "Unhealthy",                      "RED",         "TBD.", "TBD."),
        Data(250.4, 300, "Very Unhealthy",                 "PURPLE",      "TBD.", "TBD."),
        Data(500.4, 500, "Hazardous",                      "DARK_PURPLE", "TBD.", "TBD."),
    ]
    def __init__(self, pm2_5, pm10):
        self.pm2_5 = pm2_5
        self.pm10 = pm10
        self.aqi = 0
        self.aqi_data = self.AQI_TABLE[0]
        for i in range(len(self.AQI_TABLE)):
            aqi_data = self.AQI_TABLE[i]
            if self.pm2_5 < aqi_data.pm2_5:
                prev_aqi_data = self.AQI_TABLE[i - 1]
                # piecewise linear convert PM2.5 -> AQI accoridng to the AQI_TABLE
                self.aqi = (self.pm2_5 - prev_aqi_data.pm2_5) * (aqi_data.aqi_thresh - prev_aqi_data.aqi_thresh) / (aqi_data.pm2_5 - prev_aqi_data.pm2_5) + prev_aqi_data.aqi_thresh
                self.aqi_data = aqi_data
                break

    def __repr__(self):
        return self.__str__()

    def __str__(self):
        return "{} PM2.5={} PM10={} AQI={}".format(
                self.aqi_data.aqi_name,
                self.pm2_5,
                self.pm10,
                self.aqi)
        #return "{} PM2.5={} AQI={}\nPM2.5 Health Effects={}\nPrecautionary Actions={}".format(
        #        self.aqi_data.aqi_name,
        #        self.pm2_5,
        #        self.aqi,
        #        self.aqi_data.health_effects,
        #        self.aqi_data.actions)

def main():
    while True:
        data = []
        for index in range(0, 10):
            datum = ser.read()
            data.append(datum)
        #print("packet=[{}]".format(",".join([d.hex() for d in data])))

        def unpack_short(data):
            return int.from_bytes(b''.join(data), byteorder='little')

        def check_header(header):
            return header == b'\xAA'

        def check_trailer(trailer):
            return trailer== b'\xAB'

        def check_checksum(data, checksum):
            data_sum = 0
            for d in data:
                data_sum = (data_sum + int.from_bytes(d, 'little')) & 0xFF
            cs = int.from_bytes(checksum, 'little')
            #print("data_sum={} checksum={}".format(data_sum, cs))
            return data_sum == cs

        ts = datetime.now(timezone.utc)
        bad_packet = False
        valid_header = check_header(data[0])
        commander_no = data[1].hex()
        pm2_5 = unpack_short(data[2:4]) / 10
        pm10 = unpack_short(data[4:6]) / 10
        sensor_id = unpack_short(data[6:8])
        checksum = int.from_bytes(data[8], 'little')
        valid_checksum = check_checksum(data[2:8], data[8])
        valid_trailer = check_trailer(data[9])
        bad_packet = not valid_header or not valid_checksum or not valid_trailer
        #print("ts={} pm2.5={} pm10={} bad_packet={}".format(ts, pm2_5, pm10, bad_packet))
        if not bad_packet:
            print(AQI(pm2_5, pm10))
        time.sleep(1)

if __name__ == "__main__":
    main()
