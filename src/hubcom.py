#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Feb 21 11:21:01 2019
"""

from threading import Thread
from threading import Timer
import socket
import sys,os
import queue
import message
import utils
import random
# import pickle 
import time
#import netifaces as ni
from books import Books
from hashlib import sha1
from enum import Enum
import logging


FORMAT='%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


STATE_INIT = 0
STATE_UPDATE = 1
STATE_INTERESTED = 2
STATE_REQUEST = 3
STATE_CONFIRM_WRITE = 4
STATE_HUB_RECONNECT = 5
STATE_HUB_DISCONNECTED = 6
STATE_CHOKE = 7
STATE_NOT_INTERESTED = 8
STATE_SEND_HUB_NOTIFY = 9
STATE_WAIT_QUEUE = 10
STATE_PLAYER_KILLED = 11



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
    QUEUE_MSG_CHOKE = 12
    QUEUE_MSG_CHOKE_CLIENT = 13
    QUEUE_MSG_CHOKE_SERVER = 14
    QUEUE_MSG_UNCHOKE_CLIENT = 15    
    QUEUE_MSG_UNCHOKE_SERVER = 16

    QUEUE_MSG_SEND_HUB_NOTIFY = 18  
    QUEUE_MSG_KILL_CNX_PLAYER_SERVER = 19
    QUEUE_MSG_KILL_CNX_PLAYER_CLIENT = 20
    QUEUE_MSG_INTERESTED_SEND = 21
    QUEUE_MSG_NOT_INTERESTED_SEND = 22
    QUEUE_MSG_HAVE = 23
  
    QUEUE_MSG_HANDSHAKE_SERVER = 25 
    QUEUE_MSG_MANAGE_SERVER_CLIENT = 26
    
   
    
 
         
class HubCommunication(object): 
    """
    Obtain hub's port and hub's ip along with file info hash form the metafile
    Establish a connection with the hub and obtain list of players
    """
    def __init__(self, meta_file, player_id, listening_port, book, manager_queue):
        self.hub_port = meta_file.get_hub_port() # Get hub's port
        self.hub_ip = meta_file.get_hub_ip() # Get hub's ip
        
        self.hub_port = 8001
        self.hub_ip = 'localhost'     
        
        self.info_hash = meta_file.get_info_hash() # Info hash from the metafile
        self.meta_file = meta_file
        self.player_id = player_id # My player id
        self.listening_port = listening_port # My listen port
        self.book = book
        
        self.manager_q = manager_queue
        self.hub_q = queue.Queue()
        self.hub_interval = None
        self.hub_min_interval = 0
        self.hub_cnx_status = 'NOT_CONNECTED'
        self.hub_last_x_time = 0
        self.extra_log = 'H - %s'  
        
        # the connection error is managed outside
        self.hub_socket = socket.create_connection((self.hub_ip, self.hub_port)) # Create connection with the hub
        logger.debug('Start connection with hub')
        self.hub_cnx_status = 'CONNECTED'
        self.t1 = self.hub_send()
        self.t1.daemon = True
        self.t1.start()
        self.t2 = self.hub_listening()
        self.t2.daemon = True
        self.t2.start()        
        self.register_hub_queue_with_player_manager()

        left = self.meta_file.get_stuff_size() - self.book.get_downloaded_stuff_size()
        if left == 0:
            logger.debug('!!!!!!!!!The file has been completely downloaded')        
        
        
    def get_hub_queue(self):
        return self.hub_queue    
        
    def register_hub_queue_with_player_manager(self):
        self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_REGISTER_HUB_QUEUE, self.hub_q))
        
    def send_delayed_hub_notify_queue_msg(self):    
        """ function called by thread Timer to delay message 
        """
        self.hub_q.put((PlayerQMsgEnum.QUEUE_MSG_SEND_HUB_NOTIFY, STATE_SEND_HUB_NOTIFY))   

    def send_delayed_reconnect_hub_notify_queue_msg(self): 
        """ function called by thread Timer to delay message 
        """
        self.hub_q.put((PlayerQMsgEnum.QUEUE_MSG_REINIT_HUB_CNX, STATE_HUB_RECONNECT)) 

    def hub_listening(self):
        def client():
            remain = b''
            while True:
                try:
                    msg = utils.read_socket_buffer(self.hub_socket)
                except:
                    logger.debug('Hub is disconnected')
                    #self.hub_q.put((QUEUE_MSG_REINIT_HUB_CNX, STATE_HUB_RECONNECT))
                    Timer(20, self.send_delayed_reconnect_hub_notify_queue_msg).start()
                    self.hub_cnx_status = 'NOT_CONNECTED'
                    break
                if msg != b'':
                    #print(msg)
                    full_msg = remain + msg
                    status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    
                    if status == 0:
                        logger.debug('Player ' + str(self.player_id) + ' receive answer from hub')        
                        
                        # Hub has sent a new list of players
                        if objMsg.get_message_type() == 'hub answer':
                            send_timer = False
                            if self.hub_interval is None :
                                send_timer = True             
                            err_msg = objMsg.get_error()
                            warn_msg = objMsg.get_warning()
                            self.hub_interval = objMsg.get_interval()
                            self.hub_min_interval = objMsg.get_interval_min()
                            nb_seeder = objMsg.get_complete()                    
                            nb_leecher = objMsg.get_incomplete()                        
                            list_players = objMsg.get_players()
                            if send_timer == True:
                                Timer(self.hub_interval, self.send_delayed_hub_notify_queue_msg, ()).start()
                            if len(list_players):
                                #send list of players to the Player manager
                                #print('List_player' + str(list_players))
                                self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_CONNECT_PLAYERS,list_players))
                                logger.debug(self.extra_log, 'Send manager a player list ' + str(list_players))
                            else:
                                logger.debug('Player ' + str(self.player_id) + ' no player to connect to')
                                
                    elif status == -2 :
                        print('The message is corrupted')
                        #self.hub_q.put((QUEUE_MSG_REINIT_HUB_CNX, STATE_HUB_RECONNECT))
                        Timer(20, self.send_delayed_reconnect_hub_notify_queue_msg).start()
                        self.hub_socket.close()
                        self.hub_cnx_status = 'NOT_CONNECTED'
                        break 
                        
            print('Exit listening thread player ' + str(self.player_id))   
                        
        t = Thread(target=client)
        return t  
        
    def hub_send(self):         
        def client():
            state = STATE_SEND_HUB_NOTIFY
            while(True):
                if state == STATE_SEND_HUB_NOTIFY:
                    file_size = self.meta_file.get_stuff_size()
                    book_size = self.meta_file.get_book_length()
                    left = self.meta_file.get_stuff_size() - self.book.get_downloaded_stuff_size()
                   
                    logger.debug('Left to download ' + str(left))
                    
                    msg = message.HubNotifyMsg(
                                self.meta_file.get_info_hash(),
                                self.player_id,
                                self.listening_port,
                                self.book.get_downloaded_stuff_size(),
                                0,
                                left,
                                b'start').msg_encode()      
                    try:
                        self.hub_socket.sendall(msg)
                        self.hub_last_x_time = time.time()
                        logger.debug(self.extra_log, 'Player ' + str(self.player_id) + ' sent notification to hub')
                        if self.hub_interval is not None:   
                            Timer(self.hub_interval, self.send_delayed_hub_notify_queue_msg).start()
                    except:
                        logger.debug('The hub is disconnected')
                        Timer(20, self.send_delayed_reconnect_hub_notify_queue_msg).start()
                        #self.hub_q.put((PlayerQMsgEnum.QUEUE_MSG_REINIT_HUB_CNX, STATE_HUB_RECONNECT))                       
                    state = STATE_WAIT_QUEUE    
                    
                elif state == STATE_HUB_RECONNECT:
                    try:
                        try:
                            self.hub_socket.recv(1)
                        except socket.error as msg:
                            #The socket is dead and not bee restarted    
                            logger.debug('Attempt to reconnect to the hub')
                            self.hub_socket = socket.create_connection((self.hub_ip, self.hub_port)) # Create connection with the hub
                            self.hub_cnx_status = 'CONNECTED'
                            if not self.t2.isAlive():
                                self.t2 = self.hub_listening()
                                self.t2.daemon = True
                                self.t2.start()
                            state = STATE_SEND_HUB_NOTIFY                        
                    except:
                        print('Cannot connect to hub')                        
                    
                elif state == STATE_WAIT_QUEUE:                
                    try:
                        qmsg_id, info = self.hub_q.get(True, self.hub_interval)
                     
                        # a list of dead players is received
                        if qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD.value:
                            list_players = []
                            print('Dead player ' + str(info))
                            for player in info:
                               list_players.append(player['ip']+b'/'+str(player['port']).encode())
                            if len(list_players):
                                msg = message.PlayerInvalidAddrMsg(list_players).msg_encode()
                                try:
                                    self.hub_socket.sendall(msg)
                                    self.hub_last_x_time = time.time()
                                except:    
                                    print('The hub is disconnected')
                                    state = STATE_HUB_RECONNECT                                    
                                    #resend info in the queue to deal with after hub reconnection
                                    self.hub_q.put((qmsg_id, info))
                                    
                        elif qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_REINIT_HUB_CNX.value:
                            logger.debug('HubCom receive a queue message to reconnect to hub')
                            state = info                                     
                    
                        elif qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_SEND_HUB_NOTIFY.value:
                            logger.debug(self.extra_log, 'HubCom receive a queue message to notify hub')
                            state = info
                    
                    except queue.Empty: 
                        #print('Hub no msg in queue')    
                        pass     
                        
            print('Exit sending thread player ' + str(self.player_id))   
            
        t = Thread(target=client)
        return t   
        
               
                
