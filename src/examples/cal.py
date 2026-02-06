import sys
import time

import smbus3 as smbus
import phorp
import frame_streams as fs

import calcrib

class PhorpStream(calcrib.Stream):
    def __init__(self, i2c_bus):
        super().__init__('phorp')
        
        self.bus = i2c_bus        
        self.channel = None
        
        return

    def connect(self, address):
        board_index, channel_index = self.split_address(address)

        board = phorp.PhorpX4(self.bus, board_index)
        self.channel = fs.PhStream(board[int(channel_index)], 'ph_cal', filter_constant=1)

        return

    def update(self):
        self.channel.update()

        return

    def split_address(self, address):
        board_index = address[0].lower()
        channel_index = address[1]

        return (board_index, channel_index)

    @property
    def board_index(self):
        board, channel = self.split_address(self.address)

        return board

    @property
    def channel_index(self):
        board, channel = self.split_address(self.address)

        return int(channel)

    @property
    def raw_value(self):
        ''' returns a float'''
        return self.channel.raw_value
    
    @property
    def raw_units(self):
        ''' returns a string'''
        return 'V'

if __name__ == '__main__':

    config = True
    
    streams = dict()
    
    with smbus.SMBus(1) as bus:    
        stream = PhorpStream(bus)
        streams[stream.type] = stream
    
        if config == True:
            shell = calcrib.Crib(streams)
            shell.cmdloop()
        else:
            # load toml file, initialize sensors, and run
            pass

    exit()
