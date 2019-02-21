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
    """
    Super class for messages
    Input:  code: use 'value' in global dictionary variable CODE
    """
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
    
    @staticmethod
    def msg_decode(msg):
        """
        Decode buffer message_code
        return : status : 0=OK   -1=Message not complete
                 remain : part of the buffer that has not been consume during the first message decoding
                 objMsg : Message object depending on the code in the message
        usage : status, remain, objMsg = ComMessage.msg_decode(msg)         
        """
        status = 0
        
        if len(msg) < 2:
            status = -1   
            return status, msg, None        
        
        msg_length = (msg[0]<<8)+msg[1]
        if msg_length != (len(msg) - 2):
            #print(msg_length)
            #print(len(msg))
            status = -1   
            return status, msg, None
        
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
                    remain = msg[3:]
                    bitfield = bytearray(nb_bytes)
                    for i in range(0, nb_bytes):
                        bitfield[i] = remain[i]                         
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
                remain = msg[7+nb_bytes:]                
                return  status, remain, BookMsg(book_index, payload)  
                
            elif msg[2] == CODE['handshake']:  
                if msg_length != 41 :
                    raise ValueError("Message corrupted")
                else:
                    remain = msg[43:]
                    player_id = msg[3:23]
                    info_hash = msg[23:43]
                return  status, remain, HandshakeMsg(player_id, info_hash)    
                
            elif msg[2] == CODE['hub notify'] :
                sub_msg = msg[3:3+msg_length]
                info = bdecode(sub_msg)
                remain = msg[2+msg_length:]
                obj = HubNotifyMsg(info[b'info_hash'], info[b'player_id'], info[b'port'], info[b'downloaded'], info[b'uploaded'], info[b'left'], info[b'event'])
                return status, remain, obj    
               
            elif msg[2] == CODE['hub answer'] :
                sub_msg = msg[3:3+msg_length]
                info = bdecode(sub_msg)
                if b'failure reason' not in info.keys():
                    info[b'failure reason'] = b''
                if b'warning message' not in info.keys():   
                    info[b'warning message'] = b''
                remain = msg[2+msg_length:]
                obj = HubAnswerMsg(info[b'failure reason'], info[b'warning message'], info[b'interval'], info[b'min interval'], info[b'complete'], info[b'incomplete'], None)
                obj.store_players(info[b'players'])
                return status, remain, obj        

            elif msg[2] == CODE['player invalid address'] :
                sub_msg = msg[3:3+msg_length]
                info = bdecode(sub_msg)
                obj = PlayerInvalidAddrMsg(info)
                return status, remain, obj     
            else:
                print("message.py : unknow type of message")
                
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
    """ Bitfield message 
        Input: bitfield : byte array
    """    
    def __init__(self, bitfield):
        self.bitfield = bitfield  
        self.bitfield_length = len(self.bitfield)
 
        super(BitfieldMsg, self).__init__('bitfield')
        self._length = 1 + self.bitfield_length
        
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))        
        msg += self.bitfield
  
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
   
   
class HubNotifyMsg(ComMessage):
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
        super(HubNotifyMsg, self).__init__('hub notify') 
        self._length = len(self._bencode_info()) + 1
        
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
    
    def get_info_hash(self):
        return self.info_hash
        
    def get_player_id(self):
        return self.player_id
        
    def get_port(self):
        return self.port
        
    def get_downloaded(self):
        return self.downloaded
        
    def get_uploaded(self):
        return self.uploaded
        
    def get_left(self):
        return self.left
        
    def get_event(self):
        return self.event
    
    
class HubAnswerMsg(ComMessage):
    """
    Answer from the hub to the player. 
    Input :   error : if no error put b''
              warning : if no warning put b''
              interval : in seconds
              interval_min : in seconds
              players : list of dictionary item with
                                    item['ip'] = ip   as 'xxx.xxx.xxx.xxx'
                                    item['port'] = port   as integer
                                    item['complete'] = 0 or 1  
    """
    def __init__(self, error, warning, interval, min_interval, seeder_number, leecher_number, players ):
        self.error = error
        self.warning = warning
        self.interval = interval
        self.min_interval = min_interval
        self.seeder_number = seeder_number
        self.leecher_number = leecher_number
        self.players = players
        #print(self.players)        
        super(HubAnswerMsg, self).__init__('hub answer') 
        self._length = len(self._bencode_info()) + 1

    def _bencode_info(self):
        info = {}
        if self.error != b'':
            info[b'failure reason'] = self.error
        if self.warning != b'':    
            info[b'warning message'] = self.warning
        info[b'interval'] = int(self.interval)
        info[b'min interval'] = self.min_interval
        info[b'complete'] = self.seeder_number
        info[b'incomplete'] = self.leecher_number
        if self.players != None:
            nb_players = len(self.players)
            info[b'players'] = []    
            for i in range(0, nb_players):
                item = {}
                item[b'player id'] = self.players[i]['player_id']
                item[b'ip'] = bytes(self.players[i]['ip'],"utf-8")
                item[b'port'] = self.players[i]['port']
                item[b'complete'] = self.players[i]['complete']    
                info[b'players'].append(item)            
        return bencode(info)   


    def store_players(self, players_list):
        nb_players = len(players_list)
        self.players = []    
        for i in range(0, nb_players):
            item = {}
            item['player_id'] = players_list[i][b'player id']
            item['ip'] = players_list[i][b'ip']
            item['port'] = players_list[i][b'port']
            item['complete'] = players_list[i][b'complete']
            self.players.append(item)          
        
        
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))        

        msg += self._bencode_info()

        return msg        
    
    def get_error(self):
        return self.error
        
    def get_warning(self):
        return self.warning
        
    def get_interval(self):
        return self.interval
        
    def get_interval_min(self):
        return self.min_interval
    
    def get_complete(self):
        return self.seeder_number
        
    def get_incomplete(self):
        return self.leecher_number
        
    def get_players(self):
        return self.players
    
    
class PlayerInvalidAddrMsg(ComMessage): 
    """
    Create a message with a list of invalid player
    Input: invalid_players : table of bytes string of format b'IP/port'  e.g. b'127.0.0.1/7777'
    
    """
    def __init__(self, invalid_players):
        self.invalid_players = invalid_players
        super(PlayerInvalidAddrMsg, self).__init__('player invalid address') 
        self._length = len(self._bencode_info()) + 1
        
    def _bencode_info(self):
        info = {}
        nb_players = len(self.invalid_players)
        info[b'list_player'] = self.invalid_players
        return bencode(info)           
    
    def msg_encode(self):
        msg = (((self._length>>8)&0xFF).to_bytes(1, byteorder='little')) 
        msg += ((self._length&0xFF).to_bytes(1, byteorder='little'))        
        msg += ((self.message_code).to_bytes(1, byteorder='little'))        
        
        msg += self._bencode_info()
        return msg  
    
    def get_invalid_players(self):
        return self.invalid_players
        
        
        
        
        
    
if __name__ == '__main__':
    player_id = utils.generate_player_id()
    metainfo = utils.Metainfo("E:\\Dev\\Python\\BitTorrent2\\metainfo.libr")
    
    # msg = HubNotifyMsg(metainfo.get_info_hash(), player_id, 7777, 0x8000, 0x4000, 65255558, b'start').msg_encode()
    # status, remain, objMsg = ComMessage.msg_decode(msg)
    
    players = [
        {'player_id':utils.generate_player_id(), 'ip':'127.0.0.1', 'port':7896, 'complete':1},
        {'player_id':utils.generate_player_id(), 'ip':'127.0.0.1', 'port':7897, 'complete':0}
    ]
    
    msg = HubAnswerMsg(b'', b'', 100, 5, 1, 1, players ).msg_encode()
    #print(msg)
    status, remain, objMsg = ComMessage.msg_decode(msg)   
    print(objMsg.get_error())
    print(objMsg.get_warning())    
    print(objMsg.get_interval())
    print(objMsg.get_interval_min())
    print(objMsg.get_complete())
    print(objMsg.get_incomplete())
    print(objMsg.get_players())

    # invalid_players = [b'192.123.128.213/3366',b'148.253.125.32/6658',b'155.63.25.32/2356',b'126.35.98.36/8521']
    # msg = PlayerInvalidAddrMsg(invalid_players).msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage.msg_decode(msg)
    # print(objMsg.get_invalid_players())
   
    # msg = KeepAliveMsg().msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage.msg_decode(msg)
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = ChokeMsg().msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage.msg_decode(msg)    
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = UnchokeMsg().msg_encode()
    # print(msg) 
    # status, remain, objMsg = ComMessage.msg_decode(msg) 
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = InterestedMsg().msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage.msg_decode(msg) 
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())    
    
    # msg = NotInterestedMsg().msg_encode()
    # print(msg)  
    # status, remain, objMsg = ComMessage.msg_decode(msg)
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    
    # msg = HaveMsg(2562).msg_encode()
    # print(msg)
    # status, remain, objMsg = ComMessage.msg_decode(msg) 
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    # print(objMsg.get_book_index())    
    
    bitfield = bytearray([0x35, 0x26, 0xEF])
    
    msg = BitfieldMsg(bitfield).msg_encode()
    print(msg)   
    status, remain, objMsg = ComMessage.msg_decode(msg)
    print(status)
    print(remain)
    print(objMsg.get_message_type())    
    print(objMsg.get_bitfield())
    
    # msg = RequestMsg(2562).msg_encode()
    # print(msg)   
    # status, remain, objMsg = ComMessage.msg_decode(msg)  
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())
    # print(objMsg.get_book_index())
    
    # msg = BookMsg(2562, b'payload').msg_encode()
    # print(msg)     
    # status, remain, objMsg = ComMessage.msg_decode(msg)  
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())  
    # print(objMsg.get_book_index())
    # print(objMsg.get_payload())
    
    # msg = HandshakeMsg(player_id,metainfo.get_info_hash()).msg_encode()
    # print(msg) 
    # status, remain, objMsg = ComMessage.msg_decode(msg)  
    # print(status)
    # print(remain)
    # print(objMsg.get_message_type())    
    # print(objMsg.get_player_id())
    # print(objMsg.get_info_hash())    
    
    
  

    
    
  

    
    
  
