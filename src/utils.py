"""
Utils module



"""
from hashlib import sha1
import os, random
import math
import string
from bencode import bencode, bdecode
import os
import binascii

ROZALEAD_ID = b'RO0101'


class Metainfo(object):
    def __init__(self, metafile_path):
        self.metafile_path = metafile_path
        try:
            with open(metafile_path, 'br') as f:
                libr_info_bytes = f.read()
                libr_info_dict = bdecode(libr_info_bytes)
                f.close()
        except:
            print('Cannot open library file')                
                
        try:
            self._hub_ip, self._hub_port = libr_info_dict[b'announce'].split(b'/')            
        except:
            print("Incorrect format of hub address in library file")            
        
        self._hub_ip = self._hub_ip.decode("utf-8")
        self._hub_port = int(self._hub_port.decode("utf-8"))
        info_part = bencode(libr_info_dict[b'info'])
        self._info_hash = sha1(info_part).digest()
        self._stuff_length = libr_info_dict[b'info'][b'length']
        self._file_name = libr_info_dict[b'info'][b'name']       
        self._book_length = libr_info_dict[b'info'][b'piece length']

        
        if self._book_length != 0x4000:
            raise ValueError("Metainfo : incorrect book size")        
        
        self._book_number = math.ceil(self._stuff_length/self._book_length)        
        self._hashes = libr_info_dict[b'info'][b'pieces']

    def get_info_hash(self):
        return self._info_hash
    
    def get_stuff_size(self):
        return self._stuff_length
        
    def get_book_length(self):
        return self._book_length
        
    def get_hub_ip(self):
        return self._hub_ip
    
    def get_hub_port(self):
        return self._hub_port  
        
    def get_book_hash(self, book_index):
        if book_index < self._book_number:
            return self._hashes[book_index*20:(book_index+1)*20]
        else :
            return None
    
   
def generate_player_id():
    player_id = b'-' + ROZALEAD_ID + b'-' + binascii.b2a_hex(os.urandom(6))

    # for i in range(12):
    #     b = random.randint(0,255)
    #     player_id += ((b).to_bytes(1, byteorder='little'))  
        
    return player_id


def read_socket_buffer(f):
    res = b''

    dt1 = time.time_ns()

    count = 0
    #print(dt1)
    while True:
        dt2 = time.time_ns()       
        count += 1
        b = f.recv(1)
        
        if len(b) == 0:
            break
        res += b    
        if len(res) > 16 :
            break
            
        if (dt2-dt1)>1:    
            break
        time.sleep(0.000000001)    

    return res

if __name__ == '__main__':
    pass
