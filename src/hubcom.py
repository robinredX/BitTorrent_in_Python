#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from utils import PlayerQMsgEnum


FORMAT='%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel(logging.INFO)


STATE_INIT = 0
STATE_HUB_RECONNECT = 2
STATE_HUB_DISCONNECTED = 3
STATE_SEND_HUB_NOTIFY = 4
STATE_WAIT_QUEUE = 5


         
class HubCommunication(object): 
    """
    Obtain hub's port and hub's ip along with file info hash form the metafile
    Establish a connection with the hub and obtain list of players
    """
    def __init__(self, meta_file, player_id, listening_port, book, manager_queue):
        self.hub_port = meta_file.get_hub_port() # Get hub's port        
        self.hub_ip = meta_file.get_hub_ip() # Get hub's ip
        self.hub_ip = socket.gethostbyname(socket.gethostname())
        
        #self.hub_port = 8001
        #self.hub_ip = 'localhost'     
        
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
            logger.info(self.extra_log, '!!!!The file has been completely downloaded')        
        
        
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
                    logger.debug(self.extra_log, 'Hub is disconnected')
                    #self.hub_q.put((QUEUE_MSG_REINIT_HUB_CNX, STATE_HUB_RECONNECT))
                    Timer(20, self.send_delayed_reconnect_hub_notify_queue_msg).start()
                    self.hub_cnx_status = 'NOT_CONNECTED'
                    break
                    
                if msg != b'':
                    #print(msg)
                    full_msg = remain + msg
                    status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    
                    if status == 0:
                        logger.debug(self.extra_log, 'Player ' + str(self.player_id) + ' receive answer from hub')        
                        
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
                                logger.debug(self.extra_log, 'Player ' + str(self.player_id) + ' no player to connect to')
                                
                    elif status == -2 :
                        logger.error(self.extra_log, 'The message is corrupted')
                        #self.hub_q.put((QUEUE_MSG_REINIT_HUB_CNX, STATE_HUB_RECONNECT))
                        Timer(20, self.send_delayed_reconnect_hub_notify_queue_msg).start()
                        self.hub_socket.close()
                        self.hub_cnx_status = 'NOT_CONNECTED'
                        break 
                        
            logger.warning(self.extra_log, 'Exit listening thread player ' + str(self.player_id))   
                        
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
                    logger.debug(self.extra_log, 'Left to download ' + str(left))
                    
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
                        logger.debug(self.extra_log,'The hub is disconnected')
                        Timer(20, self.send_delayed_reconnect_hub_notify_queue_msg).start()   
                        
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
                        logger.warning(self.extra_log, 'Cannot connect to hub')                        
                    
                elif state == STATE_WAIT_QUEUE:                
                    try:
                        qmsg_id, info = self.hub_q.get(True, self.hub_interval)                     
                        # a list of dead players is received
                        if qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD.value:
                            list_players = []
                            logger.info(self.extra_log, 'Dead player ' + str(info))
                            for player in info:
                               list_players.append(player['ip']+b'/'+str(player['port']).encode())
                            if len(list_players):
                                msg = message.PlayerInvalidAddrMsg(list_players).msg_encode()
                                try:
                                    self.hub_socket.sendall(msg)
                                    self.hub_last_x_time = time.time()
                                except:    
                                    logger.warning(self.extra_log, 'The hub is disconnected')
                                    state = STATE_HUB_RECONNECT                                    
                                    #resend info in the queue to deal with after hub reconnection
                                    self.hub_q.put((qmsg_id, info))
                                    
                        elif qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_REINIT_HUB_CNX.value:
                            logger.debug(self.extra_log,'HubCom receive a queue message to reconnect to hub')
                            state = info                                     
                    
                        elif qmsg_id.value == PlayerQMsgEnum.QUEUE_MSG_SEND_HUB_NOTIFY.value:
                            logger.debug(self.extra_log, 'HubCom receive a queue message to notify hub')
                            state = info
                    
                    except queue.Empty: 
                        #print('Hub no msg in queue')    
                        pass     
                        
            logger.warning(self.extra_log, 'Exit sending thread player ' + str(self.player_id))   
            
        t = Thread(target=client)
        return t   
        
               
                
