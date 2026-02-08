import math
import time
import socket
import random

import gs_feedput as gs

class RollingAverage():
    def __init__(self, filter_constant, initial_value=0):
        if filter_constant < 1.0:
            filter_constant = 1.0
            
        self.n = filter_constant
        self.value= initial_value

        return

    def update(self, new_sample):
        result = self.value
        
        result -= self.value / self.n
        result += new_sample / self.n

        self.value = result
        
        return result

    
class Thermistor():
    def __init__(self, beta, r25):
        self.beta = beta
        self.r25 = r25

        self.t0 = 273.15 # freezing point of water in degrees Kelvin
        return

    def to_celcius(self, ntc_ohms):
        kelvin = self.to_kelvin(ntc_ohms)
        celcius = kelvin - self.t0
        
        return celcius

    def to_fahrenheit(self, ntc_ohms):
        celcius = self.to_celcius(ntc_ohms)
        fahrenheit = 9.0/5.0 * celcius + 32
        
        return fahrenheit

    def to_kelvin(self, ntc_ohms):
        t25 = self.t0 + 25.0
        try:
            kelvin = 1.0 / ( 1.0/t25 + (1.0/self.beta) * math.log(ntc_ohms/self.r25) )
        except ValueError:
            kelvin = 0
        
        return kelvin

    
class TemperatureStream(gs.RandomStream):
    def __init__(self, channel, location, filter_constant):
        super().__init__(channel.id, 'FLOAT')

        name = '{}.{}'.format(location, 'degF')
        self.set_name(name)
        self.set_description('Bench Temperature')
        self.set_units('fahrenheit')

        self.channel = channel
        self.channel.sample_rate = 60
        self.channel.pga_gain = 1
        self.channel.continuous = False

        #self.ntc = Thermistor(beta=3425, r25=10000)  # vishay xxx
        self.ntc = Thermistor(beta=3574.6, r25=10000) # Dwyer Instruments TE-IBN-A-18-4-8-00
        self.bias_volts = 1.5
        self.bias_ohms = 10000

        self.filter_constant = filter_constant
        self.filter = None 
        
        return

    def update(self):
        self.channel.start_conversion()
        time.sleep(self.channel.conversion_time)
        
        ntc_volts = self.channel.get_conversion_volts()
        ntc_amps = (self.bias_volts - ntc_volts) / self.bias_ohms
        ntc_ohms = ntc_volts / ntc_amps
        
        deg_f = self.ntc.to_fahrenheit(ntc_ohms)
        
        if self.filter is None:
            self.filter = RollingAverage(self.filter_constant, deg_f)
        else:
            deg_f = self.filter.update(deg_f)

        self.values.clear()
        self.values.append(round(deg_f, 1))

        return

    
class PhStream(gs.RandomStream):
    def __init__(self, channel, location, filter_constant):
        super().__init__(channel.id, 'FLOAT')

        name = '{}.{}'.format(location, 'ph')
        self.set_name(name)
        self.set_description('uncalibrated potential of Hydrogen (pH)')
        self.set_units('milli_volts')

        # self.channel = channel
        # self.channel.sample_rate = 60
        # self.channel.pga_gain = 1
        # self.channel.continuous = False
        
        self.filter = RollingAverage(filter_constant)
        
        return

    @property
    def value(self):
        ''' returns the most recent sample in engineering units'''
        return self.to_eng(self.raw_value)

    @property
    def raw_value(self):
        ''' returns the most recent sample in raw units'''
        return self.values[-1]

    def to_eng(self, raw_value):
        ''' converts raw value to engineering units'''
        return value
        
    def update(self):
        self.channel.start_conversion()
        time.sleep(self.channel.conversion_time)
        value = self.channel.get_conversion_volts()

        value = self.filter.update(value)
        
        self.values.clear()
        self.values.append(round(value, 3))
        
        return

    
class EhStream(gs.RandomStream):
    def __init__(self, stream_id, location, filter_constant):
        super().__init__(stream_id, 'FLOAT')

        name = '{}.{}'.format(location, 'eh')
        self.set_name(name)
        self.set_description('uncalibrated oxidation reduction potential (eH)')
        self.set_units('milli_volts')
        
        self.filter = RollingAverage(filter_constant)
        
        return

    def update(self):
        value = random.randrange(-7*54, 7*54)/1000*2
        value = self.filter.update(value)

        self.values.clear()
        self.values.append(round(value, 3))
        
        return

    
class Co2Stream(gs.RandomStream):
    def __init__(self, sensor, location, filter_constant):
        stream_name = 'CO2.0x{:x}'.format(sensor.address)
        super().__init__(stream_name, 'FLOAT')

        self._connect(sensor)
        
        name = '{}.{}'.format(location, 'co2')
        self.set_name(name)
        self.set_description('CO2 concentration in parts-per-million')
        self.set_units('ppm')

        self.sensor = sensor
        self.filter_constant = filter_constant
        self.filter = None
        
        return

    def _connect(self, sensor):
        retry_count = 5

        sensor.update()
        for i in range(retry_count):
            if sensor.device_id is None:
                pass
            elif 'CO2' in sensor.device_id:
                break
            else:
                time.sleep(0.3)

        if i == retry_count:
            err_str = "{}: Device at address 0x{:x} returned '{}' type. Expected 'CO2'"
            err_str = err_str.format(stream_name, sensor.address, sensor.device_id)
            raise RuntimeError(err_str)

        return
        
    def update(self):
        self.sensor.update()
        value = self.sensor.value

        if value is not None:
            # value = float(value)
            
            if self.filter is None:
                self.filter = RollingAverage(self.filter_constant, value)
            else:
                value = self.filter.update(value)
        
            self.values.clear()
            self.values.append(round(value, 1))
        
        return

    
class IpaStream(gs.PointStream):
    def __init__(self, stream_id, location):
        super().__init__(stream_id, 'STRING')

        name = '{}.{}'.format(location, 'ipa')
        self.set_name(name)
        self.set_description('Local IP Address')
        self.set_units('noSymbol')
        
        return

    def update(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # a tuple with any address...
            s.connect(('grovestreams.com', 80))
            ipa = s.getsockname()[0]
        except:
            ipa = '127.0.0.1'
        finally:
            s.close()

        self.values.clear()
        self.values.append(ipa)
        
        return

        
