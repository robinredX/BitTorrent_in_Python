"""
HubLibrary module

"""

from threading import Thread
import binascii
import socket
import queue
import os
from netutils import read_line
import numpy as np
from enum import Enum

import message
import utils
from utils import LibQMsgEnum, HubQMsgEnum

HUB_MIN_INTERVAL_CNX = 5
HUB_INTERVAL_CNX = 15

class HubLibrary(object):
    """ Manage access to the hub library which deals with the list of players
    The list of players is access through a queue to manage multiple access from different player connections
    """

    def __init__(self):
        self.lib = {}
        self.q = queue.Queue()
        t = self.consumer()
        t.daemon = True
        t.start()
        
 
    def consumer(self):
        """ Watch requests arriving in the queue to add, remove players and get player list
        """
        def consume():
            while True:
                qmsg_id, info = self.q.get()
                
                if qmsg_id.value == LibQMsgEnum.MSGQ_ADD_PLAYER_LIST.value:
                    #print('Library has received a message to add player')
                    client_queue, param, socket, addr, msg, com_time = info
                    status, remain, objMsg = message.ComMessage.msg_decode(msg)
                    if status == 0:
                        msg_type = objMsg.get_message_type()            
                        if msg_type == 'hub notify':
                            self.update_dictionary_info(objMsg, addr)
                            lib_ID = objMsg.get_info_hash()
                            player_ID = objMsg.get_player_id()
                            player_list, seeder_number, leecher_number = self.get_player_list(lib_ID, player_ID, addr, 50)
                            print('Hub player list ' + str(self.lib[lib_ID]))
                            objMsg = message.HubAnswerMsg(b'', b'', HUB_INTERVAL_CNX, HUB_MIN_INTERVAL_CNX, seeder_number, leecher_number, player_list)
                            msg = objMsg.msg_encode()
                            client_queue.put((param,(msg)))

                elif qmsg_id.value == LibQMsgEnum.MSGQ_REMOVE_PLAYER_LIST.value:
                    #print('Library has received a message to remove players')    
                    list_to_remove = {}                    
                    for cnx in info:
                        ip, port = cnx
                        for file_hash in self.lib.keys():
                            for player_id in self.lib[file_hash].keys():
                                if self.lib[file_hash][player_id]['ip'] == ip and self.lib[file_hash][player_id]['port'] == port:
                                    if file_hash not in list_to_remove.keys():
                                        list_to_remove[file_hash] = []                                     
                                    list_to_remove[file_hash].append(player_id)    
                                                        
                    for file_hash in list_to_remove.keys():
                        self.remove_player_list(file_hash, list_to_remove[file_hash])
                        
        t = Thread(target=consume)
        return t  
        
        
    def get_library_queue(self):
        return(self.q)
        

    def update_dictionary_info(self, decoded_msg, address):
        lib_file = decoded_msg.get_info_hash()
        player =  decoded_msg.get_player_id()
        port = decoded_msg.get_port()
        down = decoded_msg.get_downloaded()
        up = decoded_msg.get_uploaded()
        left = decoded_msg.get_left()
        event = decoded_msg.get_event()
        requires_reply = 0

        if event == b'start':
            #print("EVENT: start")
            try:
                self.lib[lib_file][player] = {"ip": address[0], "port": port, "complete": int(0 == left)}
            except:
                self.lib[lib_file] = {}
                self.lib[lib_file][player] = {"ip": address[0], "port": port, "complete": int(0 == left)}
            requires_reply = 1

        elif event == b'stopped':
            #print("EVENT: stopped")
            try:
                del self.lib[lib_file][player]
            except:
                print("IGNORED: no such library/player")
        elif event == b'completed':
            #print("EVENT: completed")
            if 0 == left:
                self.lib[lib_file][player]["seed"] = {int(0 == left)}

        else:
            print("something is wrong!")
        #print(self.lib)
        return requires_reply

    def remove_player_list(self, lib_file, player_list):
        #TODO consider removing from all lib_files, since connection is down
        for player_id in player_list:
            try:
                del self.lib[lib_file][player_id]
            except:
                print("IGNORED: no such library/player")
            

    def get_player_list(self, lib_ID, player_ID, address, number_requested = 50):
        seeder_number = 0
        leecher_number = 0
        
        players = np.random.choice(list(self.lib[lib_ID].keys()),size = min(len(self.lib[lib_ID]), number_requested), replace = False)
        players = np.ndarray.tolist(players)
        players.remove(player_ID)
        #print(players)        
        to_send = []
        
        for player in players:
            to_send += {'player_id': player, 'ip':self.lib[lib_ID][player]["ip"], 'port':self.lib[lib_ID][player]["port"], 'complete':self.lib[lib_ID][player]["complete"]},
            if self.lib[lib_ID][player]['complete'] == 1:
                seeder_number += 1
            else:
                leecher_number += 1

        return to_send, seeder_number, leecher_number
        
