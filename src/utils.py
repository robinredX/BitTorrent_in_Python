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
import time
from enum import Enum
ROZALEAD_ID = b'RO0101'


class LibQMsgEnum(Enum):
    MSGQ_ADD_PLAYER_LIST = 0
    MSGQ_REMOVE_PLAYER_LIST = 1
    
class HubQMsgEnum(Enum):
    MSGQ_SEND_HUB_ANSWER = 0    
    MSGQ_KILL_CNX_PLAYER = 1
    
class PlayerQMsgEnum(Enum):
    QUEUE_MSG_CONNECT_PLAYERS = 0
    QUEUE_MSG_ADD_CLIENT = 1
    QUEUE_MSG_BITFIELD = 2
    QUEUE_MSG_BITFIELD_REGISTER = 3
    QUEUE_MSG_REQUEST = 4
    QUEUE_MSG_BOOK_RECEIVED = 5
    QUEUE_MSG_PAYLOAD_READ = 6
    QUEUE_MSG_PAYLOAD_WRITE = 7
    QUEUE_MSG_REGISTER_HUB_QUEUE = 8
    QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD = 9
    QUEUE_MSG_REINIT_HUB_CNX = 10
    QUEUE_MSG_KILL_CONNECTION = 11    
    QUEUE_MSG_SEND_BITFIELD = 12
    QUEUE_MSG_CHOKE_CLIENT = 13
    QUEUE_MSG_CHOKE_SERVER = 14
    QUEUE_MSG_UNCHOKE_CLIENT = 15    
    QUEUE_MSG_UNCHOKE_SERVER = 16

    QUEUE_MSG_SEND_HUB_NOTIFY = 18  
    QUEUE_MSG_KILL_CNX_PLAYER_SERVER = 19
    QUEUE_MSG_KILL_CNX_PLAYER_CLIENT = 20
    QUEUE_MSG_INTERESTED = 21
    QUEUE_MSG_NOT_INTERESTED = 22
    QUEUE_MSG_HAVE = 23
    QUEUE_MSG_CLIENT_UPLOAD = 24
    QUEUE_MSG_HANDSHAKE_SERVER = 25 
    QUEUE_MSG_MANAGE_SERVER_CLIENT = 26 
    
    
    

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

    def get_file_name(self):
        return self._file_name.decode("utf-8")
        
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
            
    def get_book_number(self):
        return self._book_number
    
   
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
        time.sleep(0.00000001)        
        b = f.recv(32)
        dt2 = time.time_ns()         
        if len(b) == 0:
            break
        res += b    
        if len(res) > 31 :
            break            
            
            
        if (dt2-dt1)>9:    
            break
   
    return res    

    
    
if __name__ == '__main__':
    pass
