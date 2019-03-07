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
import binascii
#import netifaces as ni
from books import Books
from hashlib import sha1
from enum import Enum
from hubcom import HubCommunication
import logging
from player import PlayerConnectionManager, PlayerCommunicationClient, PlayerCommunicationServer

PLAYER_STATUS_CONNECTED = 1
PLAYER_STATUS_ACTIVE = 2
PLAYER_STATUS_INTERESTED = 4
PLAYER_STATUS_CHOKE = 8    

NB_CLIENT = 6



class TestPlayerServer(object):

    def __init__(self, player_id, meta_file, book):
        self.q = queue.Queue() 
        ip = socket.gethostbyname(socket.gethostname())            
        listening_port = 7999    
        bitfield = book.get_bitfield()
                
        # server_socket = socket.socket()
        # server_socket.bind((ip, listening_port))
        # server_socket.listen()
    
        self.connect_client(NB_CLIENT, ip, listening_port).start()
        self.server_player_dict={}
        self.client_player_dict={}

        player_manager = PlayerConnectionManager(player_id, ip, listening_port, meta_file, book, 2)
        player_manager.get_server_socket()

        while len(player_manager.server_player_list)<NB_CLIENT:
            pass
        print(player_manager.server_player_list)

        port = 7000
        for player_obj in player_manager.server_player_list:
            client_player_id = utils.generate_player_id()

            self.server_player_dict[client_player_id] = self.create_server_player(player_id, client_player_id, book, meta_file,self.q, player_obj)
            client_ip = player_obj.get_client_player_ip()
            self.client_player_dict[client_player_id] = self.create_client_player( player_id, client_player_id, book, client_ip, listening_port, meta_file, self.q, 0)
            port += 1

        player_manager.server_player_dict = self.server_player_dict
        player_manager.client_player_dict = self.client_player_dict

        status1 = [PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE|PLAYER_STATUS_INTERESTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE|PLAYER_STATUS_INTERESTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE ]
                  
        status2 = [PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_INTERESTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE,
                   PLAYER_STATUS_CONNECTED,
                   PLAYER_STATUS_CONNECTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_INTERESTED ]

        status3 = [PLAYER_STATUS_CONNECTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE|PLAYER_STATUS_INTERESTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_INTERESTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE|PLAYER_STATUS_INTERESTED,
                   PLAYER_STATUS_CONNECTED|PLAYER_STATUS_CHOKE|PLAYER_STATUS_INTERESTED  ]

        player_manager.manage_server_client()

        k = 0
        for player_id in player_manager.server_player_dict.keys():
            player_manager.server_player_dict[player_id]['status'] = status1[k]
            k += 1
        player_manager.manage_server_client()

        k = 0
        for player_id in player_manager.server_player_dict.keys():
            player_manager.server_player_dict[player_id]['status'] = status2[k]
            k += 1
        player_manager.manage_server_client()

        k = 0
        for player_id in player_manager.server_player_dict.keys():
            player_manager.server_player_dict[player_id]['status'] = status3[k]
            k += 1

        # check the selection of the interested players is balanced
        for j in range(1000):
            player_manager.manage_server_client()
            for player_id in player_manager.server_player_dict.keys():
                if not (player_manager.server_player_dict[player_id]['status'] & PLAYER_STATUS_CHOKE):
                    player_manager.server_player_dict[player_id]['nb_selected'] += 1

        time.sleep(5)
        for player_id in player_manager.server_player_dict.keys():
            print('Player ' + str(player_id) + 'nb_select=' +  str(player_manager.server_player_dict[player_id]['nb_selected']))

        print('END')

    def connect_client(self, nb_client, ip, listening_port):
        """ Waiting for new client to connect to the listening port
        """
        def client():
            count = 0            
            while count < nb_client:      
                client_socket = socket.create_connection((ip, listening_port))
                print('Client ' + str(client_socket.getsockname()))
                count += 1
                time.sleep(1)
                                                                       
        t = Thread(target=client)
        return t    


    def create_server_player(self, player_id, client_player_id, book, meta_file, q, new_player):


        server_player_item = { 'player_obj':new_player, 'status':PLAYER_STATUS_CHOKE|PLAYER_STATUS_CONNECTED,
                                                        'uploaded':0, 'time_choke_change':time.time(), 'nb_selected':0}
                                                        
        return server_player_item    


    def create_client_player(self, player_id, client_player_id, book, ip, port, meta_file, q, complete):


        client_player_item = {'bitfield':None, 'status':PLAYER_STATUS_CHOKE, 'book_request':None, 'downloaded':0, 'delay':[]}

        # new_player = PlayerCommunicationClient(player_id,
                                               # ip,
                                               # port,
                                               # client_player_id,
                                               # meta_file,
                                               # q,
                                               # book,
                                               # 30)                                          
                                               
        #logger.info(self.extra_log, '#### Connected to new client player ' + str(player['player_id']))
        client_player_item['ip'] = ip
        client_player_item['port'] = port
        client_player_item['complete'] = complete
        client_player_item['player_obj'] = None
           
        return client_player_item


class TestPlayerClient():
    """
    The objective is to test the make_request function
    """
    def __init__(self, player_id, meta_file, book):
        self.q = queue.Queue()
        ip = socket.gethostbyname(socket.gethostname())
        listening_port = 7999

        # server_socket = socket.socket()
        # server_socket.bind((ip, listening_port))
        # server_socket.listen()

        player_manager = PlayerConnectionManager(player_id, ip, listening_port, meta_file, book, 2)
        port = 7000
        bitfield = book.get_bitfield()
        self.client_player_dict = {}

        server_bitfield = bytearray(len(bitfield))

        for k in range(NB_CLIENT):
            player_id = utils.generate_player_id()
            self.client_player_dict[player_id] = {'bitfield':None, 'status':PLAYER_STATUS_CHOKE, 'book_request':None, 'downloaded':0, 'delay':[],
                                                  'ip':'127.0.0.1', 'port':port, 'seeder':0, 'player_obj':None }
            end = bytes( [bitfield[len(bitfield)-1]])

            server_bitfield[0:len(bitfield)-1] = binascii.b2a_hex(os.urandom(len(bitfield)-1))
            server_bitfield[len(bitfield)-1] = bitfield[len(bitfield)-1]
            self.client_player_dict[player_id]['bitfield'] = server_bitfield.copy()
            port += 1

        player_manager.client_player_dict = self.client_player_dict
        player_manager.make_request()

        status_list = [PLAYER_STATUS_CONNECTED, 0, PLAYER_STATUS_CONNECTED, PLAYER_STATUS_CONNECTED, 0, PLAYER_STATUS_CONNECTED]
        k = 0
        for player_id in self.client_player_dict.keys():
            player_manager.client_player_dict[player_id]['status'] |= status_list[k]
            k += 1
        player_manager.make_request()
        status_list = [PLAYER_STATUS_CHOKE, PLAYER_STATUS_CHOKE, 0, 0, PLAYER_STATUS_CHOKE, 0]
        k = 0
        for player_id in self.client_player_dict.keys():
            if not status_list[k]:
                player_manager.client_player_dict[player_id]['status'] &= ~PLAYER_STATUS_CHOKE
            else:
                player_manager.client_player_dict[player_id]['status'] |= status_list[k]
            k += 1


        for it in range(20):
            # 3 players connected and not choke   => should get 3 requests
            print('###############################')
            player_manager.make_request()
            time.sleep(1)  #to allow printing finish
            for player_id in player_manager.client_player_dict.keys():
                if player_manager.client_player_dict[player_id]['status'] & PLAYER_STATUS_ACTIVE:
                    rare = player_manager.client_player_dict[player_id]['book_request'] in player_manager.candidate_book_index
                    print('Player ' + str(player_id) + 'request book ' +
                          str(player_manager.client_player_dict[player_id]['book_request']) + ' rare=' + str(rare))
                    player_manager.client_player_dict[player_id]['book_request'] = None
                    player_manager.client_player_dict[player_id]['status'] &= ~PLAYER_STATUS_ACTIVE



def main():
    root_dir = 'E:\Test'
    meta_file_path = 'E:\Dev\Python\BitTorrent4\metainfo.libr'
    meta_file = utils.Metainfo(meta_file_path)
    player_id = b'-RO0101-7ec7150dddf3'

    book_list = []
    if player_id is None :
        print('Create player id')
        player_id = utils.generate_player_id()
    print(meta_file.get_file_name())

    print(player_id.decode("utf-8"))
    if os.path.exists(root_dir):
        player_dir = root_dir + '\\' + player_id.decode("utf-8")
        if not os.path.exists(player_dir):
            os.mkdir(player_dir)
        list_file = os.listdir(player_dir)

        if len(list_file) > 0 :
            for file in list_file:
                book_list.append(Books(player_dir+'\\'+file, meta_file))
        else:
            print('Create new stuff')
            book_list.append(Books(player_dir+'\\'+meta_file.get_file_name(), meta_file))


    #test = TestPlayerServer(player_id, meta_file, book_list[0])
    test2= TestPlayerClient(player_id, meta_file, book_list[0])




if __name__== "__main__":
    #root_dir = sys.argv[1]
    main()
    
