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
from hubcom import HubCommunication
import logging
from utils import PlayerQMsgEnum


FORMAT='%(asctime)s - %(levelname)s - %(message)s'
logging.basicConfig(format=FORMAT)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

MAX_SERVER_CONNECTION_NUMBER = 4
MAX_CLIENT_REQUEST_NUMBER = 4




#define some state in thread
STATE_INIT = 0
STATE_HUB_RECONNECT = 1
STATE_HUB_DISCONNECTED = 2
STATE_SEND_HUB_NOTIFY = 3
STATE_WAIT_QUEUE = 4
STATE_PLAYER_KILLED = 5

#define status of players : bitfield  
PLAYER_STATUS_CONNECTED = 1  # vs NOT CONNECTED
PLAYER_STATUS_ACTIVE = 2     # vs STANDBY
PLAYER_STATUS_INTERESTED = 4 # vs NOT INTERESTED
PLAYER_STATUS_CHOKE = 8      # vs UNCHOKE
    
# define to start the player in different mode for debug    
PLAYER_ROLE_SERVER_ONLY = 0
PLAYER_ROLE_CLIENT_ONLY = 1   
PLAYER_ROLE_BOTH = 2   
    
def main(root_dir, meta_file_path, player_id, role):
    """
     Read .libr file, get Meta Info and Generate player_id for out player (client).
     Contact Hub and get player list.
     Initiate connection with players and handshake.
    """
    if role==PLAYER_ROLE_SERVER_ONLY:
        print('ROLE is SERVER only')
    elif role == PLAYER_ROLE_CLIENT_ONLY:
        print('ROLE is CLIENT only')       
    
    try:
        meta_file = utils.Metainfo(meta_file_path)
    except:
        print('Cannot open library file. Terminate')
        sys.exit(-1)
        
    book_list = []
    if player_id is None :
        print('Create player id')
        player_id = utils.generate_player_id() 
    print(meta_file.get_file_name())
        
    print(player_id.decode("utf-8"))
    if os.path.exists(root_dir):
        player_dir = root_dir+'\\'+player_id.decode("utf-8")
        if not os.path.exists(player_dir):
            os.mkdir(player_dir)            
        list_file = os.listdir(player_dir)
        
        if len(list_file) > 0 :            
            for file in list_file:
                book_list.append(Books(player_dir+'\\'+file, meta_file))
        else:
            print('Create new stuff')
            book_list.append(Books(player_dir+'\\'+meta_file.get_file_name(), meta_file))
    else:
        print('The root directory does not exist. Terminate')
        sys.exit(-1)
    
    #print(book_list[0].get_bitfield())
    
    # get the ip address
    ip = socket.gethostbyname(socket.gethostname())
    print('The ip address of this player is '+str(ip))
    #ip = 'localhost'
    listening_port = random.randint(7000, 8000)
    #listening_port = 8002
    count = 0

    #Start the player manager
    while True:
        try:      
            player_cnx = PlayerConnectionManager(player_id, ip, listening_port, meta_file, book_list[0], role)
            player_manager_queue = player_cnx.get_player_manager_queue()
            break
        except:
            count += 1
            listening_port = random.randint(7000, 8000)
            if count > 50:
                print('Client: can not get a connection port. Terminate.')
                sys.exit(-1)
                break    
    

    # Start the hub communication
    count = 0
    while True :
        try :
            HubCommunication(meta_file, player_id, listening_port, book_list[0], player_manager_queue)
            print('Player ' + str(player_id) + ' connected to hub')
            break
        except:            
            count += 1
            print('Connection to hub attemp ' + str(count) + ' fail.')
            #time.sleep(5)
            if count > 5:
                print('Can not connect to the hub. Terminate.')
                sys.exit(-1)
                break
    
     
        
class PlayerConnectionManager(object):
    """ Manage the listening port and accept connection from other players
    Initiate communication with other player from the hub list
    Manage the book request for the players
    """
    def __init__(self, player_id, ip, listening_port, meta_file, book, role):
        self.player_id = player_id
        self.listening_port = listening_port
        self.meta_file = meta_file
        self.book = book
        self.role = role   
        self.extra_log = 'M - %s'   
        
        self.server_socket = socket.socket()
        self.server_socket.bind((ip, listening_port))       
        self.server_socket.listen()    
        logger.info(self.extra_log, 'Player ' + str(self.player_id) + ' listening ' + str(ip) + ':' + str(listening_port))
        self.q = queue.Queue()
        self.hub_q = None

        self.candidate_book_index = [] #set to global for test
        #The client player that have connected to this player server
        self.server_player_list = []
        #The client player that have connected to this player server and send an hancheck
        self.server_player_dict = {}
        #The player server this player has connected to
        self.client_player_dict = {}
        
        self.server_thread_timer = None        
        self.server_manager_time = time.time()
        t1 = self.consume_manager_queue()
        t1.daemon = True
        t1.start()
        if self.role != PLAYER_ROLE_CLIENT_ONLY:        
            t2 = self.player_waiting_connection()
            t2.daemon = True
            t2.start()
        t3 = self.manage_player_request()
        t3.daemon = True
        t3.start()
        

    def get_server_socket(self):
        return self.server_socket

    def get_player_manager_queue(self):
        return self.q

    def player_waiting_connection(self):
        """ Waiting for new client to connect to the listening port
        """
        def client():
            logger.debug('Waiting for client connection')
            while True:       
                client_socket, addr = self.server_socket.accept()   
                logger.debug(self.extra_log, 'Received connection', client_socket)            
                new_player = PlayerCommunicationServer(self.player_id,
                                                       self.book,
                                                       client_socket,
                                                       addr,
                                                       self.meta_file,
                                                       self.q,
                                                       50)
                logger.info(self.extra_log, '##### Connect new server player ' + str(addr))                                       
                self.q.put((PlayerQMsgEnum.QUEUE_MSG_ADD_CLIENT,new_player))    
                                                                       
        t = Thread(target=client)
        return t           
    
    def check_client_players_alive(self):
        """ Check that the client players thread are still running 
           (i.e. nothing strange happened)    
        """
        for client_player in self.server_player_list:
            if not client_player.is_client_alive():
                logger.debug(self.extra_log, 'Remove client player ' + str(client_player.get_client_player_id()))
                self.server_player_list.remove(client_player)               
    
    def manage_player_request(self):
        """ Manage the selection of book to request from players
        """
        def handle():
            while True:
                if self.role != PLAYER_ROLE_SERVER_ONLY:
                    self.make_request()
                self.check_client_players_alive()
                #time.sleep(1)

        t = Thread(target=handle)
        return t

    def is_existing_player(self, player):
        player_id  = player['player_id']
        logger.debug(self.extra_log, 'Check existing player ' + str(player))
        if player_id in self.client_player_dict.keys():
            # if 'ip' not in self.client_player_dict[player_id] :
                # logger.warning(self.extra_log, 'Need to check ip ', self.client_player_dict[player_id])
            if self.client_player_dict[player_id]['ip'] == player['ip']:
                return True
            else:
                return False
        else:
            return False
            
    def check_is_player_fraud(self, player):
    
        key = player['player_id']
        if key in self.client_player_dict.keys():
            if self.client_player_dict[key]['ip'] != player['ip']:
                return True
            else :
                return False
        return False
            
    def send_server_client_manage_message(self):
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_MANAGE_SERVER_CLIENT, None))
        
    def add_book_index(self, bitfield, book_index):
        """ add book index to the client bitfield
        """
        byte_index = book_index // 8
        bit_index = book_index % 8
        shift_index = 8 - (bit_index + 1)
        byte_mask = 1 << shift_index       
        bitfield[byte_index] |= byte_mask 
        
        return bitfield
        
    def consume_manager_queue(self):
        def queue_consumer():
            while True:
                q_msg_id, info = self.q.get()
                
                if q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_REGISTER_HUB_QUEUE.value:
                    #logger.debug('Hub has registered its queue')
                    self.hub_q = info
                                
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_CONNECT_PLAYERS.value:
                    if self.role != PLAYER_ROLE_SERVER_ONLY:
                        list_player = info
                        logger.debug(self.extra_log, 'Manager receive queue message to connect players ' + str(list_player))           
                        
                        if len(list_player):
                            dead_player_list = []
                            for player in list_player:
                                if self.is_existing_player(player):
                                    # This player is already connected and running
                                    logger.debug(self.extra_log, 'C- Existing player ' + str(player['player_id']))
                                    self.client_player_dict[player['player_id']]['port'] = player['port']
                                
                                    # if self.check_is_player_fraud(player):
                                        # logger.error(self.extra_log, 'Mismatch between player_id and ip: reject player ' + str(player))
                                        # fraud_player = self.client_player_dict[player['player_id']]['player_obj']
                                        # fraud_player.kill_player()

                                else:                                    
                                    self.client_player_dict[player['player_id']] = {'bitfield':None, 'status':PLAYER_STATUS_CHOKE, 'book_request':None, 'downloaded':0, 'delay':[]}

                                    try:
                                        self.client_player_dict[player['player_id']]['ip'] = player['ip']
                                        self.client_player_dict[player['player_id']]['port'] = player['port']
                                        new_player = PlayerCommunicationClient(self.player_id,
                                                                               player['ip'],
                                                                               player['port'], player['player_id'],
                                                                               self.meta_file,
                                                                               self.q,
                                                                               self.book,
                                                                               30)
                                        logger.info(self.extra_log, '#### Connected to new client player ' + str(player['player_id']))
                                        
                                        self.client_player_dict[player['player_id']]['seeder'] = player['complete']
                                        self.client_player_dict[player['player_id']]['player_obj'] = new_player
                                        
                                    except:
                                        logger.warning(self.extra_log, 'Player cannot connect to player server ' + str(player['player_id']))
                                        dead_player_list.append(player)
                                        
                            if len(dead_player_list):                       
                                if self.hub_q is not None:
                                    self.hub_q.put((PlayerQMsgEnum.QUEUE_MSG_NOTIFY_HUB_PLAYER_DEAD, dead_player_list))
                                     
                                        
                        else:
                            logger.debug(self.extra_log, 'No players in the list')

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_ADD_CLIENT.value:                      
                    client = info
                    logger.debug('Manager add client ' + str(client))
                    self.server_player_list.append(client) 
                    #print(self.server_player_list)

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_HANDSHAKE_SERVER.value:
                    # the server has received a handshake from a client player 
                    client, client_player_id = info
                    remove_player = None
                    # remove the server client from list to dict
                    for player in self.server_player_list :
                        if player == client:                            
                            if client_player_id not in self.server_player_dict.keys():
                                self.server_player_dict[client_player_id] = {   'player_obj':client,
                                                                                'status':PLAYER_STATUS_CHOKE|PLAYER_STATUS_CONNECTED,
                                                                                'uploaded':0,
                                                                                'time_choke_change':time.time()}                                
                                remove_player = player
                                break
                    if remove_player != None:
                        self.server_player_list.remove(remove_player)
                        
                    if self.get_server_not_choke_client_number() < MAX_SERVER_CONNECTION_NUMBER and self.get_server_choke_client_number():
                        #print(self.server_thread_timer)
                        # try to unchoke client immediately
                        if self.server_thread_timer != None:                            
                            if self.server_thread_timer.is_alive() :
                                self.server_thread_timer.cancel()
                                logger.debug(self.extra_log, 'Cancel server manger timer ' + str(self.server_thread_timer.is_alive()))
                                self.send_server_client_manage_message()
                            #otherwise the message is in queue
                        else :
                            logger.info(self.extra_log, 'Request manager check to unchoke player t=' + str(time.time()))
                            self.server_thread_timer = Timer(5, self.send_server_client_manage_message).start() 

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_CLIENT_UPLOAD.value:
                    client_player_id, data_length = info
                    if client_player_id in self.server_player_dict.keys():
                        self.server_player_dict[client_player_id]['uploaded'] += data_length
                    
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_INTERESTED.value:
                    # the server has received a message that a client is interested
                    player_id = info
                    if player_id in self.server_player_dict.keys():
                        self.server_player_dict[player_id]['status'] |= PLAYER_STATUS_INTERESTED
      
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_NOT_INTERESTED.value:                         
                    # the server has received a message that a client is not interested
                    player_id = info
                    if player_id in self.server_player_dict.keys():
                        self.server_player_dict[player_id]['status'] &= ~PLAYER_STATUS_INTERESTED

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_CHOKE_CLIENT.value:
                    client_player_id = info
                    if client_player_id in self.client_player_dict.keys():
                        self.client_player_dict[client_player_id]['status'] |= PLAYER_STATUS_CHOKE  
                        logger.debug(self.extra_log, 'Client ' + str(client_player_id) + ' status : ' + str(bin(self.client_player_dict[client_player_id]['status'])))                           
                            
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_UNCHOKE_CLIENT.value:  
                    client_player_id = info
                    if client_player_id in self.client_player_dict.keys():
                        self.client_player_dict[client_player_id]['status'] &= ~PLAYER_STATUS_CHOKE   
                        logger.info(self.extra_log, 'Client ' + str(client_player_id) + ' status : ' + str(bin(self.client_player_dict[client_player_id]['status'])))   
                        
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_BITFIELD_REGISTER.value:
                    logger.debug(self.extra_log, 'Manager received bitfield to register')
                    client_player_id, bitfield = info
                    #print(client_player_id)
                    
                    self.client_player_dict[client_player_id]['bitfield'] = bitfield
                    if not self.client_player_dict[client_player_id]['status'] & PLAYER_STATUS_CONNECTED :                    
                        self.client_player_dict[client_player_id]['status'] |= PLAYER_STATUS_CONNECTED
                        self.client_player_dict[client_player_id]['status'] &= ~PLAYER_STATUS_ACTIVE
                        #print(self.client_player_dict)
                    #if the bitfield was resent because sth happened    
                    if self.client_player_dict[client_player_id]['status'] & PLAYER_STATUS_ACTIVE :  
                        if self.book.have_book(self.client_player_dict[client_player_id]['book_request'], bitfield):
                            #the requested book is not there anymore
                            self.client_player_dict[client_player_id]['status'] &= ~PLAYER_STATUS_ACTIVE
                            self.client_player_dict[client_player_id]['book_request'] = None
                    self.make_interested(client_player_id, True)
                    
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_SEND_BITFIELD.value: 
                    #in case the file has been restore then send bitfield update to all players
                    for player_id in self.server_player_dict.keys():
                        self.server_player_dict[player_id]['player_obj'].send_bitfield()              
      
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_HAVE.value:
                    client_player_id, book_index = info
                    logger.debug(self.extra_log, 'Update bitfield from player ' + str(client_player_id))
                    
                    if client_player_id in self.client_player_dict.keys():
                        self.client_player_dict[client_player_id]['bitfield'] = self.add_book_index(self.client_player_dict[client_player_id]['bitfield'], book_index)
                        # the bitfield of the client player is update need to signify if we are interested
                        self.make_interested(client_player_id, False)
                    else:
                        logger.warning(self.extra_log, 'Player manager cannot find the player ' + str(client_player_id) + ' to update bitfield')

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_BOOK_RECEIVED.value:
                    client_player_id, book_index, data_length, delay = info
                    logger.info(self.extra_log, 'Manager receive confirmation of book ' + str(book_index) + ' from player ' + str(client_player_id))
                    if client_player_id in self.client_player_dict.keys():
                        if self.client_player_dict[client_player_id]['book_request'] == book_index:
                            self.client_player_dict[client_player_id]['downloaded'] += data_length
                            #logger.info(self.extra_log, 'Downloaded size is ' + str(self.client_player_dict[client_player_id]['downloaded']))
                            self.client_player_dict[client_player_id]['delay'].append(delay)
                            #keep only the 10 last delay measure
                            if len(self.client_player_dict[client_player_id]['delay']) > 10:
                                self.client_player_dict[client_player_id]['delay'].pop(0)
                            self.client_player_dict[client_player_id]['book_request'] = None
                            self.client_player_dict[client_player_id]['status'] &= ~PLAYER_STATUS_ACTIVE
                    
                    for player_id in self.server_player_dict.keys():
                        self.server_player_dict[player_id]['player_obj'].send_have_message(book_index)
                        
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_KILL_CNX_PLAYER_CLIENT.value:
                    kill_player_id, ip = info
                    logger.info(self.extra_log, 'Player manager receive notification a client player has been killed with id = ' + str(kill_player_id))
                    #remove the player from the dictionnary
                    if kill_player_id in self.client_player_dict.keys():
                        if self.client_player_dict[kill_player_id]['ip'] == ip:
                            del self.client_player_dict[kill_player_id]
                            self.kill_player_server(kill_player_id, ip)                            

                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_KILL_CNX_PLAYER_SERVER.value:
                    logger.debug(self.extra_log, 'Player manager receive notification kill server player')
                    player, kill_player_id, ip = info
                    nb_client_player = len(self.server_player_list)
                    if kill_player_id in self.server_player_dict.keys():
                        del self.server_player_dict[kill_player_id] 
                        self.kill_player_client(kill_player_id)                        
                    
                    for i in range(0, nb_client_player):
                        if self.server_player_list[i] == player:                       
                            logger.debug(self.extra_log, 'Player manager remove client ' + str(kill_player_id) + 'client thread alive = ' + str(self.server_player_list[i].is_client_alive()))
                            self.server_player_list.pop(i)
                            self.kill_player_client(kill_player_id)
                            break
                                
                elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_MANAGE_SERVER_CLIENT.value:   
                    logger.debug(self.extra_log, 'Manager check to unchoke player t=' + str(time.time()))
                    if self.server_thread_timer != None:
                        if self.server_thread_timer.is_alive() :
                            self.server_thread_timer.cancel()   
                            self.server_thread_timer = None                          
                
                    self.manage_server_client()
                    self.server_thread_timer = Timer(30, self.send_server_client_manage_message).start()    

        t = Thread(target=queue_consumer)
        return t 
        
        
    def kill_player_client(self, player_id) :
        if player_id in self.client_player_dict.keys():
            if 'player_obj' in self.client_player_dict[player_id].keys():
                self.client_player_dict[player_id]['player_obj'].kill_player()
        else:
            logger.debug(self.extra_log, 'Cannot find a client player with ' + str(player_id) + ' to kill')
            #print(self.client_player_dict)
   
        
    def kill_player_server(self, kill_player_id, kill_ip) :
        logger.info(self.extra_log, 'Need to kill ' + str(kill_player_id) + ' and ip ' + str(kill_ip))
        found_player = False
        # check if the server player is registered
        if kill_player_id in self.server_player_dict.keys():        
            player_ip = self.server_player_dict[kill_player_id]['player_obj'].get_client_player_ip()
            #print('Player IP ' + str(player_ip))
            #print('Kill IP' + str(kill_ip))
            if player_id == kill_player_id and player_ip == kill_ip:
                self.server_player_dict[kill_player_id]['player_obj'].kill_player()                
                logger.info(self.extra_log, 'Kill player ' + str(kill_player_id) + ' with ip ' + str(kill_ip))  
                found_player = True                
            
        if found_player == False:
            logger.debug(self.extra_log, 'Cannot find a server player with ' + str(kill_player_id) + ' to kill')
                
    def check_book_not_requested(self, book_index):
        is_requested = True
        for player_id in self.client_player_dict.keys():            
            if self.client_player_dict[player_id]['status'] == 'ACTIVE':
                if self.client_player_dict[player_id]['book_request'] == book_index:
                    is_requested = False
        return is_requested        

    def make_interested(self, player_id, send_notify): # Whether to send interested message or not
        #print('Manager check if interested by client ' + str(player_id))
        if player_id in self.client_player_dict.keys():
            if self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED:               
                self.client_player_dict[player_id]['missing_book'] = self.book.match_bitfield(self.client_player_dict[player_id]['bitfield'])                
                if self.client_player_dict[player_id]['missing_book'] != []:
                    if not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_INTERESTED) or (send_notify==True):
                        logger.info(self.extra_log, 'Manager notify interested to player ' + str(player_id))
                        self.client_player_dict[player_id]['player_obj'].send_interested()
                    self.client_player_dict[player_id]['status'] |= PLAYER_STATUS_INTERESTED
                else:         
                    if (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_INTERESTED) or (send_notify==True):
                        logger.info(self.extra_log, 'Manager notify NOT interested to player '+ str(player_id))
                        self.client_player_dict[player_id]['player_obj'].send_not_interested()
                    self.client_player_dict[player_id]['status'] &= ~PLAYER_STATUS_INTERESTED #not interested
                
    def get_player_dowload_size(self, player_id): 
        """Get how much was download from a player
        """
        if player_id in self.client_player_dict.keys():
            return self.client_player_dict[player_id]['downloaded']
        else:
            return 0            
     
    def get_server_not_choke_client_number(self):
        nb_client = 0
        for player_id in self.server_player_dict.keys():
            if not (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                nb_client += 1
        return nb_client  
        
    def get_server_choke_client_number(self):
        nb_client = 0
        for player_id in self.server_player_dict.keys():
            if (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                nb_client += 1
        return nb_client   
        
    def get_not_choke_player(self):
        list_player = []
        for player_id in self.server_player_dict.keys():
            if not (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                list_player.append(player_id)  
        return list_player 
        
    def get_not_interested_not_choke_player(self):
        list_player = []
        for player_id in self.server_player_dict.keys():
            if not (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_INTERESTED) and \
                             not (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                list_player.append(player_id)  
        return list_player  
        
    def get_interested_choke_player(self):
        list_player = []
        for player_id in self.server_player_dict.keys():
            if (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_INTERESTED) and \
                             (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                list_player.append(player_id) 
        return list_player 

    def get_interested_player(self):
        list_player = []
        for player_id in self.server_player_dict.keys():
            if (self.server_player_dict[player_id]['status'] & PLAYER_STATUS_INTERESTED):
                list_player.append(player_id) 
        return list_player 
 
    def manage_server_client(self):
        logger.info('#!#!#!#!# Manage server client dt=' + str(time.time() - self.server_manager_time))
        self.server_manager_time = time.time()
        
        list_i = self.get_interested_player()
        nb_i = len(list_i)
        #no clients are interested
        if nb_i == 0:
            return
        
        nb_not_choke_client = self.get_server_not_choke_client_number()
        nb_choke_client = self.get_server_choke_client_number()
        logger.info(self.extra_log, 'S- The number of interested server client is ' + str(nb_i))

        #logger.info(self.extra_log, self.server_player_dict)
        
        # simple case we can unchoke all interested and choke not interested
        if nb_i <= MAX_SERVER_CONNECTION_NUMBER:
            #print('S- simple case')
            list_i_c = self.get_interested_choke_player()
            list_ni_nc = self.get_not_interested_not_choke_player()

            for player_id in self.server_player_dict.keys():
                if player_id not in list_i and player_id in list_ni_nc:
                    logger.info(self.extra_log, 'S- Manager request choke message to client ' + str(player_id))
                    self.server_player_dict[player_id]['player_obj'].send_choke()
                    self.server_player_dict[player_id]['status'] |= PLAYER_STATUS_CHOKE
                    self.server_player_dict[player_id]['time_choke_change'] = time.time()
                elif player_id in list_i_c :
                    logger.info(self.extra_log, 'S- Manager request unchoke message to client ' + str(player_id))
                    self.server_player_dict[player_id]['player_obj'].send_unchoke()
                    self.server_player_dict[player_id]['status'] &= ~PLAYER_STATUS_CHOKE
                    self.server_player_dict[player_id]['time_choke_change'] = time.time()

            for player_id in self.server_player_dict.keys():
                downloaded_size = self.get_player_dowload_size(player_id)
                logger.info(self.extra_log, 'client ' + str(player_id) + ' status ' + \
                                str(bin(self.server_player_dict[player_id]['status'])) + ' \t download '\
                                + str(downloaded_size) + '\t upload ' + str(self.server_player_dict[player_id]['uploaded']))

        else:
            logger.debug(self.extra_log, 'S- There are more interested players than connection')
            list_noti_notc = self.get_not_interested_not_choke_player()
            list_i_c = self.get_interested_choke_player()
            nb_i_c = len(list_i_c)
            nb_noti_notc = len(list_noti_notc)
            logger.debug(self.extra_log, 'S- There are ' + str(nb_i_c) + ' interested and choke players')
            logger.debug(self.extra_log, 'S- There are ' + str(nb_noti_notc) + ' NOT interested and unchoke players')
            if nb_i_c :
                if nb_noti_notc:
                    # some players are not interested and unchoke => choke
                    random.shuffle(list_noti_notc) 
                    k = 0
                    while k < nb_i_c and k < nb_noti_notc:
                        player_id = list_noti_notc[k]
                        self.server_player_dict[player_id]['player_obj'].send_choke()
                        self.server_player_dict[player_id]['status'] |= PLAYER_STATUS_CHOKE
                        self.server_player_dict[player_id]['time_choke_change'] = time.time()        
                        k += 1
                        
                list_not_c = self.get_not_choke_player()
                nb_not_c = len(list_not_c)
                logger.info(self.extra_log, 'S- There are ' + str(nb_not_c) + ' unchoke players')
                if nb_i_c <= (MAX_SERVER_CONNECTION_NUMBER - nb_not_c):
                    # can unchoke everybody as enough connection
                    logger.debug(self.extra_log, 'S- Enough connection to unchoke all interested')
                    for player_id in list_i_c:
                        self.server_player_dict[player_id]['player_obj'].send_unchoke()
                        self.server_player_dict[player_id]['status'] &= ~PLAYER_STATUS_CHOKE
                        self.server_player_dict[player_id]['time_choke_change'] = time.time()  
                
                else : 
                    # pick randomly among all interested players
                    # those who are already unchoke are also considered
                    #print('S - Need to select who to choke')
                    list_i = self.get_interested_player()
                    random.shuffle(list_i) 
                    if len(list_i) <= MAX_SERVER_CONNECTION_NUMBER :
                        list_selected = list_i
                    else:
                        list_selected = list_i[0:MAX_SERVER_CONNECTION_NUMBER]
                        
                    logger.debug(self.extra_log, 'S- Selected players are ' + str(list_selected))
                    #choke the one that are unchoke and not selected
                    list_not_c = self.get_not_choke_player()
                    for player_id in list_not_c:
                        if player_id not in list_selected :
                            # player not selected => choke
                            self.server_player_dict[player_id]['player_obj'].send_choke()
                            self.server_player_dict[player_id]['status'] |= PLAYER_STATUS_CHOKE
                            self.server_player_dict[player_id]['time_choke_change'] = time.time()                             
              
                    for player_id in list_selected:
                        if player_id not in list_not_c :
                            self.server_player_dict[player_id]['player_obj'].send_unchoke()
                            self.server_player_dict[player_id]['status'] &= ~PLAYER_STATUS_CHOKE
                            self.server_player_dict[player_id]['time_choke_change'] = time.time()    
                            
            else:    
                logger.debug(self.extra_log, 'S- All interested are unchoked -> nothing to do')            
            for player_id in self.server_player_dict.keys():
                downloaded_size = self.get_player_dowload_size(player_id)
                logger.info(self.extra_log, 'S- client ' + str(player_id) + ' status ' + str(bin(self.server_player_dict[player_id]['status'])) \
                                         + ' \t download ' + str(downloaded_size) + '\t upload ' + str(self.server_player_dict[player_id]['uploaded']) )


    def get_active_client_player(self):
        player = []
        for player_id in self.client_player_dict.keys():
            if (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED) and \
                      (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_ACTIVE) and \
                      not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                player.append(player_id)
        return player

    def get_standby_client_player(self):
        player = []
        for player_id in self.client_player_dict.keys():
            if (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED) and \
                         not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_ACTIVE) and \
                         not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE) :
                player.append(player_id)
        return player

    def get_connected_client_player(self):
        player = []
        for player_id in self.client_player_dict.keys():
            if self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED:
                player.append(player_id)
        return player

    def get_unchoke_client_player(self):
        player = []
        for player_id in self.client_player_dict.keys():
            if (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED) and not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE) :
                player.append(player_id)
        return player

    def make_request(self):
        bitfield = self.book.get_bitfield()
        if self.book.missing_books(bitfield) == []:
            # no book need to be downloaded
            return

        list_connected = self.get_connected_client_player()
        if len(list_connected) == 0:
            # no connected player bye
            return

        list_unchoke = self.get_unchoke_client_player()
        if len(list_unchoke) == 0:
            # no unchoke server bye
            return

        list_active = self.get_active_client_player()
        list_standby = self.get_standby_client_player()
        nb_active_players = len(list_active)
        nb_standby_players = len(list_standby)
        #print('There are '+ str(nb_active_players) + ' active players')
        loop = 0
        logger.debug(self.extra_log, 'C- Number of active client players ' + str(nb_active_players))
        logger.debug(self.extra_log, 'C- Number of standby client players ' + str(nb_standby_players))
        
        while nb_active_players < MAX_CLIENT_REQUEST_NUMBER and nb_standby_players:
        
            logger.debug(self.extra_log, 'C- Loop ' + str(loop))
            book_count = {}
            for player_id in self.client_player_dict.keys():
                if self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED:
                    self.client_player_dict[player_id]['missing_book'] = self.book.match_bitfield(self.client_player_dict[player_id]['bitfield'])

            #get the count of book presence amoung the different players
            for player_id in self.client_player_dict.keys():
                if (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED):
                    for book_no in self.client_player_dict[player_id]['missing_book']:    
                        if book_no in book_count.keys():
                            book_count[book_no] += 1
                        else:
                            book_count[book_no] = 1
            
            #get the list of book_index by increasing frequence number among the other players
            freq_key=[]            
            for key, value in sorted(book_count.items(), key=lambda item: (item[1], item[0])):
                freq_key.append(key)

            if len(freq_key):
                player_found = False
                first_freq_index = 0
                while player_found == False:
                    ## maybe a loop here first_freq_index
                    self.candidate_book_index = []
                    # get the frequency of the rarest book
                    frequency = book_count[freq_key[first_freq_index]]
                    #get all book with same frequency
                    idx = first_freq_index
                    while idx<len(freq_key) and book_count[freq_key[idx]] == frequency:
                        self.candidate_book_index.append(freq_key[idx])
                        idx += 1

                    logger.debug(self.extra_log, 'Candidate book with freq=' + str(frequency) + ' ' + str(self.candidate_book_index))
                    # scan random table of rarest book index
                    if len(self.candidate_book_index):
                        #random.seed(time.time_ns())
                        random.shuffle(self.candidate_book_index)
                        for book_index in self.candidate_book_index:
                            list_book_owner = []
                            if self.check_book_not_requested(book_index) == True:
                                #print('the book is available')
                                for player_id in self.client_player_dict.keys():
                                    if (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CONNECTED) \
                                             and not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE) \
                                             and not (self.client_player_dict[player_id]['status'] & PLAYER_STATUS_ACTIVE):
                                        if book_index in self.client_player_dict[player_id]['missing_book']:
                                            list_book_owner.append(player_id)
                                            logger.info(self.extra_log, 'C- Player ' + str(player_id) + ' can accept index ' + str(book_index) +' book request ')
                                if len(list_book_owner):
                                    player_found = True
                                    break

                    if player_found == False:
                        # search other candidate with higher frequency as no player available with lower freq
                        while first_freq_index < len(freq_key) and book_count[freq_key[first_freq_index]] == frequency:
                            first_freq_index += 1

                        if first_freq_index == len(freq_key):
                            logger.debug(self.extra_log, 'There are no book to use')
                            break

                if len(list_book_owner):
                    logger.info(self.extra_log, 'C- Book index ' + str(book_index) + ' has players')
                    picked_player_id = random.choice(list_book_owner)
                    logger.info(self.extra_log, 'C- Manager send request book ' + str(book_index) + ' to player ' + str(picked_player_id))
                    if self.client_player_dict[picked_player_id]['player_obj'] != None:   #to make it run in test mode
                        self.client_player_dict[picked_player_id]['player_obj'].get_client_queue().put((PlayerQMsgEnum.QUEUE_MSG_REQUEST, book_index))
                    self.client_player_dict[picked_player_id]['book_request'] = book_index
                    self.client_player_dict[picked_player_id]['status'] |= PLAYER_STATUS_ACTIVE
                else:
                    #print('No more players available')
                    break
            else :
                # There are no book to fetch
                #print('No book to fetch')
                break
                
            list_active = self.get_active_client_player()
            list_standby = self.get_standby_client_player()
            nb_active_players = len(list_active)
            nb_standby_players = len(list_standby)
            logger.debug('C- There are '+ str(nb_active_players) + ' active players' + ' and ' + str(nb_standby_players) + ' standby player')
            loop += 1
        #print('Exit make request')


class PlayerCommunicationClient(object):
    """
    Manage communication with one player server.
    Initiate two threads to listen and send to the  player server.
    """
    def __init__(self, player_id, client_ip, client_listening_port, client_player_id, meta_file, manager_queue, book, max_connections): # Maximum number of connections
       
        self.client_listening_port = client_listening_port
        self.client_player_id = client_player_id
        self.client_ip = client_ip
        self.player_id = player_id
        self.meta_file = meta_file
        self.book = book
        self.manager_q = manager_queue
        self.info_hash = meta_file.get_info_hash()
        self.q = queue.Queue() 
        self.client_bitfield = None
        self.client_choke = False
        self.player_interested = None
        self.extra_log = 'S - %s'
        # connection error is managed outside
        self.client_socket = socket.create_connection((self.client_ip, self.client_listening_port))
        self.t1 = self.handle_client_listen()
        self.t1.daemon = True
        self.t1.start()
        self.t2 = self.handle_client_send()
        self.t2.daemon = True
        self.t2.start()
        self.requested_book = None
        self.request_time = 0
        self.reception_delay = 0
        self.extra_log = 'C - %s'
        
    def add_book_index(self, book_index):
        """ add book index to the client bitfield
        """
        byte_index = book_index // 8
        bit_index = book_index % 8
        shift_index = 8 - (bit_index + 1)
        byte_mask = 1 << shift_index

        self.client_bitfield[byte_index] |= byte_mask           
        
    def kill_player(self):
        try:
            self.client_socket.close()
        except :            
            pass
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION, None))
        
    def get_client_queue(self):
        return self.q 
     
    def get_client_player_id(self):
        return self.client_player_id
        
    def send_interested(self):
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_INTERESTED, None))
        
    def send_not_interested(self):
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_NOT_INTERESTED, None))   
        
    def handle_client_listen(self):
        def client():
            remain = b''
            while True:
                try :
                    msg = utils.read_socket_buffer(self.client_socket)               
                except:
                    self.q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION, None))
                    logger.warning(self.extra_log, 'Killing listening client player ' + str(self.client_player_id))                
                    break
                    
                if msg != b'': 
                    full_msg = remain + msg
                    #print(full_msg)      
                    try :
                        status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    except ValueError:
                        status = -2
                        logger.error(self.extra_log, 'Message is corrupted')
                    
                    if status == 0:   
                        msg_id = objMsg.get_message_type()
                        #print('Client msd id = ' + str(msg_id))
                        if msg_id == 'bitfield':
                            logger.info(self.extra_log, 'Got bitfield message from player ' + str(self.client_player_id))
                            self.client_bitfield = objMsg.get_bitfield()
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_BITFIELD_REGISTER, (self.client_player_id, self.client_bitfield)))

                        elif msg_id == 'have':
                            book_index = objMsg.get_book_index()
                            self.add_book_index(book_index)
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_HAVE, (self.client_player_id, book_index)))   
                            
                        elif msg_id == 'choke': 
                            logger.debug(self.extra_log, 'choke message received' + ' at t=' + str(time.time()))    
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_CHOKE_CLIENT, (self.client_player_id)))
                            self.client_choke = True
                            
                        elif msg_id == 'unchoke':
                            logger.debug(self.extra_log, 'unchoke message received' + ' at t=' + str(time.time()))
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_UNCHOKE_CLIENT, (self.client_player_id)))
                            self.client_choke = False                            
                            
                        elif msg_id == 'book':    
                            logger.debug(self.extra_log, 'receive book message')
                            if objMsg.get_book_index() == self.requested_book:
                                payload = objMsg.get_payload()
                                if self.meta_file.get_book_hash(self.requested_book) == sha1(payload).digest():
                                    self.reception_delay = time.time()-self.request_time
                                    logger.info(self.extra_log, 'Book received in ' + str(self.reception_delay) + ' from player ' + str(self.client_player_id))
                              
                                    self.book.queue_write(self.requested_book, payload, (self.q, PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_WRITE))

                                else:
                                    logger.error(self.extra_log, 'Book signature mismatch')
                            else:
                                logger.error(self.extra_log, 'This was not what book index I requested')
                                
                    elif status == -2:
                        logger.error(self.extra_log, 'The message is corrupted - Disconnect the client player')
                        logger.debug(full_msg)                        
                        self.q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION, None))
                        logger.warning(self.extra_log, 'Killing listening client player ' + str(self.client_player_id))
                        self.client_socket.close()
                        break  
            
            logger.warning(self.extra_log, 'Exit listening thread client player ' + str(self.client_player_id)) 
                        
        t = Thread(target=client)
        return t          
  
        
    def handle_client_send(self):
        def client():
            state = STATE_INIT
            while True:
                if state == STATE_INIT:
                    handshake_send = message.HandshakeMsg(self.player_id, self.meta_file.get_info_hash()).msg_encode()
                    self.client_socket.sendall(handshake_send)
                    logger.info(self.extra_log, 'Send handshake to player ' + str(self.client_player_id))
                    state = STATE_WAIT_QUEUE
                
                elif state == STATE_WAIT_QUEUE:
                    q_msg_id, info = self.q.get()

                    if q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_REQUEST.value:
                        logger.debug(self.extra_log, 'Receive send request for player ' + str(self.client_player_id) + ' and server_ckoke=' + str(self.client_choke)  + ' at t=' + str(time.time()))
    
                        if self.client_choke == False :
                            self.requested_book = info
                            if self.requested_book is not None:
                                logger.debug(self.extra_log, 'A request from manager has been received for client ' + str(self.client_player_id))              
                                request_send = message.RequestMsg(self.requested_book).msg_encode()
                                self.client_socket.sendall(request_send)
                                self.request_time = time.time() 
                        else :
                            # other player didn't respect choke state. Shall we shut connection with player?
                            logger.error('Player ' + str(self.client_player_id) + ' did not respect choked state')
                                
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_WRITE.value:
                        #send a confirmation to the player manager that a book has been received
                        book_index, data_length, result = info
                        if result >= 0 :
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_BOOK_RECEIVED, (self.client_player_id, book_index, data_length, self.reception_delay)))
                            logger.debug(self.extra_log, 'Confirm to manager writing of book ' + str(self.requested_book))
                        if result == 1 :
                            # the stuff file has disappear but book is written
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_SEND_BITFIELD, None))
                            logger.info(self.extra_log, 'The stuff file has restarted from 0. Request resend bitfield')
                        self.request_time = 0
                        self.reception_delay = 0
                        self.requested_book = None
                        
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_INTERESTED.value:
                        # in bittorrent protocol we should express interested/ not interested msg even if we are choke
                        if self.player_interested != True:                        
                            interested_send = message.InterestedMsg().msg_encode()
                            self.client_socket.sendall(interested_send)
                            logger.debug(self.extra_log, 'Send interested to player ' + str(self.client_player_id))
                            self.player_interested = True
                            
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_NOT_INTERESTED.value:
                        # in bittorrent protocol we should express interested/ not interested msg even if we are choke
                        if self.player_interested != False:
                            not_interested_send = message.NotInterestedMsg().msg_encode()
                            self.client_socket.sendall(not_interested_send)
                            logger.debug(self.extra_log, 'Send not interested to player ' + str(self.client_player_id))
                            self.player_interested = False
                        
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION.value :

                        logger.debug(self.extra_log, 'Killing sending client player ' + str(self.client_player_id))
                        self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CNX_PLAYER_CLIENT, (self.client_player_id, self.client_ip)))
                        state = STATE_PLAYER_KILLED
                        break
                        
                elif state == STATE_PLAYER_KILLED:
                    logger.error(self.extra_log, 'Player killed ' + str(self.client_player_id))
                    time.sleep(30)
                    
            logger.warning(self.extra_log, 'Exit sending thread client player ' + str(self.client_player_id))                 
                        
        t = Thread(target=client)
        return t  
        
   


class PlayerCommunicationServer(object):
    """
    Manage communication with one player as client.
    Initiate two threads to listen and send to the  player server.
    """
    def __init__(self, player_id, book, client_socket, addr, meta_file, manager_queue, max_connections): # Maximum number of connections
        self.addr = addr
        self.client_socket = client_socket
        self.player_id = player_id
        self.meta_file = meta_file
        self.book = book
        self.manager_q = manager_queue
        self.q = queue.Queue() 
        self.client_player_id = None
        self.client_bitfield = None
        self.client_interested = False
        self.client_choke = True
        self.extra_log = 'S - %s'
        self.time_cnx = time.time()

        self.t1 = self.handle_client_listen()
        self.t1.daemon = True
        self.t1.start()
        self.t2 = self.handle_client_send()
        self.t2.daemon = True
        self.t2.start()         

       
    def kill_player(self):    
        try:
            self.client_socket.close()
        except :
            pass
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION, None))
        
    def is_client_alive(self):
        if self.t1.isAlive() and self.t2.isAlive():
            return True
        else:
            return False
            
    def get_client_player_id(self):
        return self.client_player_id
        
    def get_client_player_ip(self): 
        return self.addr[0].encode()


    def send_have_message(self, book_index):
        """ put message in the queue to send message have to other players
        """
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_HAVE, book_index))        

    def send_bitfield(self):
        """ put message in the queue to send message bitfield to other players
        """    
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_BITFIELD, None))
        
    def send_choke(self):
        """ put message in the queue to send message choke to other players
        """ 
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_CHOKE_SERVER, None))
    
    def send_unchoke(self):
        """ put message in the queue to send message unchoke to other players
        """     
        self.q.put((PlayerQMsgEnum.QUEUE_MSG_UNCHOKE_SERVER, None))
    
    def handle_client_listen(self):    
        def client():
            remain = b''
            while True:
                try :            
                    msg = utils.read_socket_buffer(self.client_socket)
                except:
                    self.q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION, None))
                    logger.warning(self.extra_log, 'Killing listening client player ' + str(self.client_player_id))                   
                    break
                if msg != b'':
                    full_msg = remain + msg
                    try :
                        status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    except ValueError:
                        status = -2
                        logger.error(self.extra_log, '!!!!!!!!!!!Message is corrupted')
                        
                    if status == 0:  
                        msg_id = objMsg.get_message_type()
                        if msg_id == 'handshake': # Received handshake, put in queue to send bitfield                            
                            self.client_player_id = objMsg.get_player_id()
                            logger.info(self.extra_log, 'Receive handshake message from player ' + str(self.client_player_id) + ' with adr ' + str(self.addr))
                            self.q.put((PlayerQMsgEnum.QUEUE_MSG_BITFIELD,None))  
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_HANDSHAKE_SERVER, (self, self.client_player_id)))

                        elif msg_id == 'interested': # Received interested message, put in queue of inetersted clients
                            logger.debug(self.extra_log, 'Receive interested message from player ' + str(self.client_player_id))    
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_INTERESTED, self.client_player_id ))
                            self.client_interested = True
                        
                        elif msg_id == 'not interested': # Received handshake, put in queue of not interested clients
                            logger.debug(self.extra_log, 'Receive not interested message from player ' + str(self.client_player_id))
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_NOT_INTERESTED, self.client_player_id ))                            
                            self.client_interested = False
                            
                        elif msg_id == 'request': # Received a request message, get book index
                            book_index = objMsg.get_book_index()
                            logger.info(self.extra_log, 'Receive request message book ' + str(book_index) + ' for player ' + str(self.client_player_id) + 
                                               ' with interest=' + str(self.client_interested) + ' choke=' + str(self.client_choke))
                            if self.client_interested == True and self.client_choke == False : 
                                # the request is sent to book manager, the book manager send the answer via the player queue
                                self.book.queue_read(book_index, (self.q, PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_READ))
                            else:
                                logger.debug(self.extra_log, 'Book request received but the client was not interested or choked') # TODO How to deal with this? Can this happen?                                

                            
                    elif status == -2:
                        logger.error(self.extra_log, 'S- The message is corrupted - Disconnect the server player')
                        #print(full_msg)
                        self.q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION, None))
                        logger.warning(self.extra_log, 'S- Killing listening client player ' + str(self.client_player_id))
                        try:
                            self.client_socket.close()
                        except :
                            pass
                        break
                        
            logger.warning(self.extra_log, 'Exit listening thread server player ' + str(self.client_player_id))  
            
        t = Thread(target=client)
        return t          
        
        
    def handle_client_send(self):
        def client():
            state = STATE_WAIT_QUEUE            
            if state == STATE_WAIT_QUEUE:
                while True:
                    q_msg_id, info = self.q.get()  
                    msg_send = b''                    
                    if q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_BITFIELD.value:
                        # A bitfield has been requested by a client player
                        msg_send = message.BitfieldMsg(self.book.get_bitfield()).msg_encode()
                        logger.info(self.extra_log, 'Send bitfield to player ' + str(self.client_player_id))

                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_HAVE.value:  
                        # need to send a message have to other players after a book has been received
                        book_index = info
                        msg_send = message.HaveMsg(book_index).msg_encode()
                        logger.debug(self.extra_log, 'Send have message to player ' + str(self.client_player_id))
                                
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_CHOKE_SERVER.value: # Send choke message
                        logger.debug(self.extra_log, 'Send choke to player ' + str(self.client_player_id) + ' at t=' + str(time.time()))
                        msg_send = message.ChokeMsg().msg_encode()                        
                        self.client_choke = True
                        
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_UNCHOKE_SERVER.value : # Send unchoke message                        
                        logger.debug(self.extra_log, 'Send unchoke to player ' + str(self.client_player_id) + ' at t=' + str(time.time()))
                        msg_send = message.UnchokeMsg().msg_encode()                        
                        self.client_choke = False               
                
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_PAYLOAD_READ.value and self.client_choke == False : # Receive queue for sending books and send book
                        # A book is to be send a client player
                        # The message comes from the books manager
                        logger.debug(self.extra_log, 'Received payload from book manager for player ' + str(self.client_player_id))
                        book_index, payload = info
                        if payload != None :
                            msg_send = message.BookMsg(book_index, payload).msg_encode()                        
                            # notify manager to update 'uploaded'                      
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_CLIENT_UPLOAD,(self.client_player_id, len(payload))))
                        else:
                            #the file is corrupted
                            self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_SEND_BITFIELD, None))
                            logger.info(self.extra_log, 'The stuff file has restarted from 0. Request resend bitfield')
    
                    elif q_msg_id.value == PlayerQMsgEnum.QUEUE_MSG_KILL_CONNECTION.value :
                        logger.warning(self.extra_log, 'Killing sending server player ' + str(self.client_player_id))
                        self.manager_q.put((PlayerQMsgEnum.QUEUE_MSG_KILL_CNX_PLAYER_SERVER, (self, self.client_player_id, self.addr)))
                        state = STATE_PLAYER_KILLED
                        break
                      
                    if msg_send != b'':
                        try:                            
                            self.client_socket.sendall(msg_send)                            
                        except:
                            logger.error(self.extra_log, 'Cannot reach player socket ' + str(self.client_player_id) )
                            state = STATE_PLAYER_KILLED
                            break

                      
            elif state == STATE_PLAYER_KILLED:
                # shouldn't come her
                logger.error(self.extra_log, 'Player killed ' + str(self.client_player_id))
                time.sleep(30)      
            
            logger.warning(self.extra_log, 'Exit sending thread server player ' + str(self.client_player_id))  

            
        t = Thread(target=client)
        return t          
        
    # logger.critical('This is a critical message.')
# logger.error('This is an error message.')
# logger.warning('This is a warning message.')
# logger.info('This is an informative message.')
# logger.debug('This is a low-level debug message.')    
                       
if __name__== "__main__":

    try:
        root_dir = sys.argv[1]
        meta_file_path = sys.argv[2]
        player_id = sys.argv[3] 
    except:
        print('usage: player.py root_dir library_file player_id')
        print('player_id can be None')
        print()
        sys.exit(-1)
    try:
        role = int(sys.argv[4])
    except:
        role = 2   
    
    if player_id == 'None':
        player_id = None
    else :
        player_id = player_id.encode()
  
    #player_id = b'-RO0101-7ec7150dddf3'
    main(root_dir, meta_file_path, player_id, role)
