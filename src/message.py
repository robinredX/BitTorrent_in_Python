"""
Message generator module



"""

from hashlib import sha1
import os
import math
import string
import utils
from bencode import bencode, bdecode

CODE = {
    'keep alive':None,
    'choke':0x00,
    'unchoke':0x01,
    'interested':0x02,
    'not interested':0x03,
    'have':0x04,
    'bitfield':0x05,
    'request':0x06,
    'book':0x07,
    'handshake':0x08,
    
    'hub notify':0x10,
    'hub answer':0x11,
    'player invalid address':0x12
    
    }
    
    
class ComMessage(object):
    def __init__(self, code):
        self.message_code = None
        if code != None :
            self.message_code = CODE[code]
        self._length = 0
        if self.message_code == CODE['choke'] or self.message_code == CODE['unchoke'] or \
            self.message_code == CODE['interested'] or self.message_code == CODE['not interested']:        
            self._length = 1        
    
    def get_message_type(self):
        if self.message_code == None :
            return 'keep alive'           
        for msg, code in CODE.items():   
            if code == self.message_code:    
                return msg
        return None

    
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))
        if self.message_code == CODE['choke'] or self.message_code == CODE['unchoke'] or \
                self.message_code == CODE['interested'] or self.message_code == CODE['not interested']:            
            msg += ((self.message_code).to_bytes(1, byteorder='little'))                  
        return msg
    
    def msg_decode(self, msg):
        """
        Decode buffer message_code
        return : status : 0=OK   -1=Message not complete
                 remain : part of the buffer that has not been consume bay the message_code
                 objMsg : Message object depending on the code in the message
        usage : status, remain, objMsg = ComMessage(None).msg_decode(msg)         
        """
        status = 0
        msg_length = (msg[0]<<8)+msg[1]
       
        if msg_length != (len(msg) - 2):
            status = -1   
            return status, msg
        
        elif msg_length != 0 :
            remain = msg[4:]
            if msg[2] == CODE['choke']:
                return status, remain, ChokeMsg()
            elif msg[2] == CODE['unchoke']:     
                return status, remain, UnchokeMsg()
            elif msg[2] == CODE['interested']:              
                return status, remain, InterestedMsg()
            elif msg[2] == CODE['not interested']:  
                return status, remain, NotInterestedMsg()
            elif msg[2] == CODE['have']: 
                if msg_length != 5 :
                    raise ValueError("Message corrupted")
                else:
                    book_index = 0
                    for i in range(0,4):
                        book_index = book_index<<8 | msg[3+i]
                    remain = msg[7:]                    
                return status, remain, HaveMsg(book_index)
            elif msg[2] == CODE['bitfield']: 
                if msg_length < 2 :
                    raise ValueError("Message corrupted")            
                else :
                    nb_bytes = msg_length - 1
                    remain = msg[3+nb_bytes:]
                    bitfield = 0
                    for i in range(nb_bytes):
                        bitfield = bitfield<<8 | msg[3+i]                      
                return  status, remain, BitfieldMsg(bitfield)               
            elif msg[2] == CODE['request']:  
                if msg_length != 5 :
                    raise ValueError("Message corrupted")
                else:
                    remain = msg[7:]
                    book_index = 0
                    for i in range(0,4):
                        book_index = book_index<<8 | msg[3+i]              
                return  status, remain, RequestMsg(book_index)  
            elif msg[2] == CODE['book']:  
                book_index = 0
                for i in range(0,4):
                    book_index = book_index<<8 | msg[3+i]            
                nb_bytes = msg_length - 5  
                payload = msg[7:7+nb_bytes]                
                return  status, remain, BookMsg(book_index, payload)                  
            elif msg[2] == CODE['handshake']:  
                if msg_length != 41 :
                    raise ValueError("Message corrupted")
                else:
                    remain = msg[43:]
                    player_id = msg[3:23]
                    info_hash = msg[23:43]
                return  status, remain, HandshakeMsg(player_id, info_hash)         
     
        else:
            remain = msg[2:]
            return status, remain, KeepAliveMsg()           
            
    
    
        
        
class KeepAliveMsg(ComMessage):
    def __init__(self):
        super(KeepAliveMsg, self).__init__('keep alive')   

class ChokeMsg(ComMessage):
    def __init__(self):
        super(ChokeMsg, self).__init__('choke')   
        
class UnchokeMsg(ComMessage):
    def __init__(self):
        super(UnchokeMsg, self).__init__('unchoke')      

class InterestedMsg(ComMessage):
    def __init__(self):
        super(InterestedMsg, self).__init__('interested')   
        
class NotInterestedMsg(ComMessage):
    def __init__(self):
        super(NotInterestedMsg, self).__init__('not interested')   
   
class HaveMsg(ComMessage):
    def __init__(self, book_index):
        self.book_index = book_index  
        super(HaveMsg, self).__init__('have')    
        self._length = 5

    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))
        for i in range(0, 4):
            msg += ((self.book_index >> 8*(3-i))&0xFF).to_bytes(1, byteorder='little')
        return msg

    def get_book_index(self):
        return self.book_index

        
class BitfieldMsg(ComMessage):
    def __init__(self, bitfield):
        self.bitfield = bitfield  
        
        nb_bytes = 0       
        index = self.bitfield
        while index:
            index = index >> 8
            nb_bytes += 1    
        super(BitfieldMsg, self).__init__('bitfield')
        self._length = 1 + nb_bytes
        
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))
        
        nb_bytes = self._length - 1
        for i in range(0, nb_bytes):
            msg += ((self.bitfield >> 8*(nb_bytes-1-i))&0xFF).to_bytes(1, byteorder='little')
        return msg        
     
    def get_bitfield(self):
        return self.bitfield
       
class RequestMsg(ComMessage):
    def __init__(self, book_index):
        self.book_index = book_index     
        super(RequestMsg, self).__init__('request')  
        self._length = 5

    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))

        for i in range(0, 4):
            msg += ((self.book_index >> 8*(3-i))&0xFF).to_bytes(1, byteorder='little')
        return msg

    def get_book_index(self):
        return self.book_index        
        

class BookMsg(ComMessage):
    def __init__(self, book_index: int, payload: bytes):
        self.book_index = book_index  
        self.payload = payload
        super(BookMsg, self).__init__('book')    
        self._length = 5 + len(payload)
        
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))

        for i in range(0, 4):
            msg += ((self.book_index >> 8*(3-i))&0xFF).to_bytes(1, byteorder='little')
        
        msg += self.payload            
        return msg
      
    def get_book_index(self):
        return self.book_index
        
    def get_payload(self):
        return self.payload
        
class HandshakeMsg(ComMessage):
    def __init__(self, player_id, info_hash):
        self.player_id = player_id
        self.info_hash = info_hash
        super(HandshakeMsg, self).__init__('handshake')          
        self._length = 41
        
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))        
        
        msg += self.player_id
        msg += self.info_hash
        return msg        
   
    def get_player_id(self):
        return self.player_id
        
    def get_info_hash(self):
        return self.info_hash
   
   
class HubNotify(ComMessage):
    """
        Hub notification : message sent from player to hub to register
    """
    def __init__(self, info_hash: bytes, player_id: bytes, port:int, downloaded:int, uploaded:int, left:int, event: bytes):
        self.info_hash = info_hash
        self.player_id = player_id
        self.port = port
        self.downloaded = downloaded
        self.uploaded = uploaded
        self.left = left
        self.event = event    
        super(HubNotify, self).__init__('hub notify') 
        self._length = len(self._bencode_info()) + 3
        
        
    def _bencode_info(self):
        info = {}
        info[b'info_hash'] = self.info_hash 
        info[b'player_id'] = self.player_id
        info[b'port'] = self.port
        info[b'downloaded'] = self.downloaded
        info[b'uploaded'] = self.uploaded
        info[b'left'] = self.left
        info[b'event'] = self.event

        return bencode(info)
    
    
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))        
        
        msg += self._bencode_info()
        return msg
    
    
class HubAnswer(ComMessage):
    def __init__(self, error, warning, interval, min_interval, seeder_number, leecher_number, players ):
        self.error = error
        self.warning = warning
        self.interval = interval
        self.min_interval = min_interval
        self.seeder_number = seeder_number
        self.leecher_number = leecher_number
        self.players = players
        super(HubAnswer, self).__init__('hub notify') 
        self._length = len(self._bencode_info()) + 3


    def _bencode_info(self):
        info = {}
        # if self.error != None:
            # info[b'failure reason'] = self.error
        # if self.warning != None:    
            # info[b'warning message'] = self.warning
        info[b'interval'] = int(self.interval)
        info[b'min interval'] = self.min_interval
        info[b'complete'] = self.seeder_number
        info[b'incomplete'] = self.leecher_number
        nb_players = len(players)
        info[b'players'] = []        
        # for i in range(0, nb_players):
            # item = {}
            # item[b'player id'] = players[i]['player_id']
            # item[b'ip'] = players[i]['ip']
            # item[b'port'] = players[i]['port']
            # item[b'complete'] = players[i]['complete']    
            # info[b'players'].append(item)
            
        # print(info)    
        return bencode(info)   
   
    
   
if __name__ == '__main__':
    player_id = utils.generate_player_id()
    metainfo = utils.Metainfo("E:\\Dev\\Python\\BitTorrent2\\metainfo.libr")
    
    msg = HubNotify(metainfo.get_info_hash(), player_id, 7777, 0x8000, 0x4000, 65255558, b'start').msg_encode()
    print(msg)
    
    players = [
        {'player_id':utils.generate_player_id(), 'ip':'127.0.0.1', 'port':7896, 'complete':1},
        {'player_id':utils.generate_player_id(), 'ip':'127.0.0.1', 'port':7897, 'complete':0}
    ]
    
    msg = HubAnswer(b'', b'', 100, 5, 1, 1, players )
    
    
    
   
    # msg = KeepAliveMsg().msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = ChokeMsg().msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)    
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = UnchokeMsg().msg_encode()
    # print(msg) 
    # status, remain, objMsg = ComMessage(None).msg_decode(msg) 
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = InterestedMsg().msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage(None).msg_decode(msg) 
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())    
    
    # msg = NotInterestedMsg().msg_encode()
    # print(msg)  
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = HaveMsg(2562).msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage(None).msg_decode(msg) 
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    # print(objMsg.get_book_index())    
    
    # msg = BitfieldMsg(0x3526EF).msg_encode()
    # print(msg)   
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())    
    # print(hex(objMsg.get_bitfield()))
    
    # msg = RequestMsg(2562).msg_encode()
    # print(msg)   
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)  
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    # print(objMsg.get_book_index())
    
    # msg = BookMsg(2562, b'payload').msg_encode()
    # print(msg)     
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)  
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())  
    # print(objMsg.get_book_index())
    # print(objMsg.get_payload())
    
    # msg = HandshakeMsg(player_id,metainfo.get_info_hash()).msg_encode()
    # print(msg) 
    # status, remain, objMsg = ComMessage(None).msg_decode(msg)  
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())    
    # print(objMsg.get_player_id())
    # print(objMsg.get_info_hash())    
    
    
  
