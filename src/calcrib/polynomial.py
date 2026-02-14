import datetime

from . import procedure
from . import setpoint as sp
from . import equation

class PolynomialProcedure(procedure.ProcedureShell):
    def __init__(self, streams, *kwargs):
        super().__init__(streams, *kwargs)

        self.parameters = dict()
        self.point_count = 2
        
        return

    @property
    def p1(self):
        return self.parameters['p1']

    @property
    def p2(self):
        return self.parameters['p2']

    @property
    def p3(self):
        return self.parameters['p3']
        
    # def do_spread(self, arg):
    #     ''' spread <n> Calibration point count, 2 or 3'''
        
    #     try:
    #         if int(arg) > len(self.parameters): # not in [2,3]:
    #             print(' possible point count is {}'.format([2,3]))
    #         else:
    #             self.point_count = int(arg)
    #     except:
    #         print(' possible choices are 2 or 3')
            
    #     self.do_show()
        
    #     return False

    def do_p1(self, arg):
        ''' p1 <n> The first (lowest value) in a two or three point calibration'''
        
        try:
            self.p1.scaled_value = float(arg)
        except:
            print(' invalid value: setpoint unchanged.')

        self.do_show()
        
        return False
        
    def do_p2(self, arg):
        ''' p2 <n> The middle or highest value in a two or three point calibration'''
        
        try:
            self.p2.scaled_value = float(arg)
        except:
            print(' invalid value: setpoint unchanged.')

        self.do_show()
        
        return False
        
    def do_p3(self, arg):
        ''' p3 <n> The highest value in a three point calibration'''
        
        if self.point_count < 3:
            print(' there is no point 3 in a two point calibration')
        else:
            self.p3.scaled_value = float(arg)

        self.do_show()
        
        return False
        
    def show(self):
        print('  Units:  {}'.format(self.scaled_units))
        print('  Spread: {} point'.format(self.point_count))
        print('   P1:    {} {}'.format(self.p1.scaled_value, self.p1.scaled_units))
        print('   P2:    {} {}'.format(self.p2.scaled_value, self.p2.scaled_units))
        if self.point_count == 3:
            print('   P3:   {} {}'.format(self.p3.scaled_value, self.p3.scaled_units))

        return

    def prep(self, sensor):
        if sensor.calibration.equation is None:
            sensor.calibration.equation = PolynomialEquation()
        
        # give sensor its own copy of paramters
        sensor.parameters = dict()
        sensor.parameters[self.p1.name] = self.p1.clone()
        sensor.parameters[self.p2.name] = self.p2.clone()
        if self.point_count == 3:
            sensor.parameters[self.p2.name] = self.p3.clone()

        super().prep(sensor)

        return
        
    def cal(self, sensor):
        print(' running {} point calibration on sensor {}'.format(self.point_count, sensor.id))
        ok = True

        # run thru the setpoints
        for parameter in sensor.parameters.values():
            # if parameter.name in ['p1', 'p2', 'p3']:
            if not parameter.run(sensor):
                ok = False
                break

        if ok:
            p1 = sensor.parameters['p1']
            p2 = sensor.parameters['p2']

            ok = sensor.calibration.equation.generate(p1.scaled_value,p1.mean, p2.scaled_value,p2.mean)
                
        return ok

    def pack(self, prefix):
        package = super().pack(prefix)
        package += 'point_count = {}\n'.format(self.point_count)

        my_prefix = '{}.{}'.format(prefix, 'parameters')
        for parameter in self.parameters.values():
            parameter_prefix = '{}.{}'.format(my_prefix, parameter.name)
            package += '\n'
            package += parameter.pack(parameter_prefix)
        
        return package

    def unpack(self, package):
        super().unpack(package)
        self.point_count = package['point_count']

        if 'parameters' in package:        
            for template in package['parameters'].values():
                parameter = sp.Setpoint('','','')
                parameter.unpack(template)
                self.parameters[parameter.name] = parameter
            
        return
    
class PolynomialEquation(equation.Equation):
    def __init__(self, package=None):
        super().__init__()
        
        self.degree = 1
        self.coefficients = dict()
        self.coefficients[0] = 0.0
        self.coefficients[1] = 1.0

        if package:
            self.unpack(package)

        return

    def __len__(self):
        return len(self.coefficients)

    def generate(self, x1,y1, x2,y2):
        self.timestamp = datetime.date(1970, 1, 1)

        is_valid = False
        try:
            self.coefficients[1] = (y2 - y1) / (x2 - x1)
            self.coefficients[0] = y1 - self.coefficients[1] * x1
            
            is_valid = True
        except ZeroDivisionError:
            self.coefficients[1] = 0.00001
            self.coefficients[0] = 0.0
            
        return is_valid

    def evaluate_x(self, x_value):
        y = self.coefficients[1] * x_value + self.coefficients[0]
        
        return y

    def evaluate_y(self, y_value):
        slope = self.coefficients[1]
        if slope == 0:
            slope = 0.00001

        x = (y_value - self.coefficients[0]) / slope
        
        return x
    
    # def dump(self):
    #     for key, value in self.coefficients.items():
    #         print(key, round(value, 3))

    #     return
    
    def pack(self, prefix):
        package = super().pack(prefix)

        package += 'degree = {}\n'.format(self.degree)

        package += '[{}.{}]\n'.format(self.package_prefix, 'coefficients')
        for key, value in self.coefficients.items():
            package += '{} = {}\n'.format(key, value)

        return package

    def unpack(self, package):
        super().unpack(package)
        
        self.degree = package['degree']
        
        for name, value in package['coefficients'].items():
            self.coefficients[int(name)] = value
        
        return

