"""
HubClient module

"""
from threading import Thread
import binascii
import socket
import queue
import os
from netutils import read_line
import numpy as np
import time
from enum import Enum

import message
import utils
from utils import LibQMsgEnum, HubQMsgEnum



class HubPlayer(object):
    def __init__(self, player_socket, addr, lib_q):
        self.player_socket = player_socket
        self.addr = addr
        self.lib_q = lib_q
        self.file_hash = None
        self.player_id = None
        #the queue is used to send instructions to the handle_client_send thread
        self.q = queue.Queue()
        t1 = self.handle_client_listen()
        t1.daemon = True
        t1.start()
        t2 = self.handle_client_send()
        t2.daemon = True
        t2.start() 
        
            #time-out defaults to 10 seconds for testing purposes,
            #and only checks the IP
            #this makes more sense than playerID, since the latter is self-generated
            #and makes more sense than checking the port also, since we could be 
            #spamming the hub from multiple client instances on the same machine
            #TODO make sure it matches the hub answer interval
            
    # handle_client returns a Thread that can be started, i.e., use: handle_client(.......).start()
    def handle_client_listen(self):
        """ listen to the client player 
        """
        def handle():
            #print("Create thread listen")
            count=0
            remain = b''
            while True:
    
                try:
                    msg = utils.read_socket_buffer(self.player_socket)
                except :  
                    print('Communication with player '+ str(self.player_id) + ' has been interupted. ' )
                    self.q.put((HubQMsgEnum.MSGQ_KILL_CNX_PLAYER, None))
                    break      
                    
                if msg != b'':
                    #print(msg)
                    full_msg = remain + msg
     
                    try :
                        status, remain, objMsg = message.ComMessage.msg_decode(full_msg)  
                    except ValueError:
                        status = -2
                        print('!!!!!!!!!!!Message is corrupted')
                        
                    if status == 0:
                        msg_type = objMsg.get_message_type()    
                        
                        # Receive hub notify message    
                        if msg_type == 'hub notify':
                            if self.player_id == None:
                               self.player_id  =  objMsg.get_player_id()        
                               
                            print('Player '+ str(self.player_id) + ' Hub notify received from ' + str(self.addr) + ' at ' + str(time.time()))
                            len_msg = len(full_msg) - len(remain)
                            
                            self.lib_q.put((LibQMsgEnum.MSGQ_ADD_PLAYER_LIST, (self.q, HubQMsgEnum.MSGQ_SEND_HUB_ANSWER,
                                                                                       self.player_socket,
                                                                                       self.addr,full_msg[0:len_msg], time.time())))
                        
                        # Receive invalid player message
                        elif msg_type == 'player invalid address':
                            invalid_players = objMsg.get_invalid_players()
                            print('Receive invalid player list' + str(invalid_players[b'list_player']))
                            list_dead_players=[]                            
                            for player_cnx in invalid_players[b'list_player']:                                
                                ip, port = player_cnx.split(b'/',1)
                                # try :
                                    # socket.create_connection((ip.decode("utf-8"),int(port)))
                                # except : 
                                    # print('Fail attempt to connect to ' + str((ip.decode("utf-8"),int(port))))
                                    
                                list_dead_players.append((ip.decode("utf-8"),int(port)))
                                    
                            if len(list_dead_players):
                                self.lib_q.put((LibQMsgEnum.MSGQ_REMOVE_PLAYER_LIST, list_dead_players))
                            
                            print('Send requets to remove player')
                            
                        else:
                            print('Player '+ str(self.player_id) + 'Received invalid message type')

                    elif status == -2:
                        print('The message is corrupted - Disconnect the server player')
                        print(full_msg)
                        self.q.put((HubQMsgEnum.MSGQ_KILL_CNX_PLAYER, None))
                        print('Killing player ' + str(self.player_id))
                        try:
                            self.client_socket.close()
                        except :
                            pass
                        break
        
            print('Exit listening thread player ' + str(self.player_id))

        t = Thread(target=handle)
        return t


    def handle_client_send(self):
        """ Manage the sending of messages to the client player
            Request to send a message are sent via a queue
        """
        def handle():
            #print("Create thread send")       
            while True :
                #Waiting to receive message from client queue
                qmsg_id, info = self.q.get()
                #print('Client receive message from lib')
                if qmsg_id.value == HubQMsgEnum.MSGQ_SEND_HUB_ANSWER.value :
                    msg = info 
                    try:
                        self.player_socket.sendall(msg)
                        print('Player ' + str(self.player_id) + ' Message sent to player')
                    except :
                        print('The connection is not established anymore')
                        break
                        
                elif qmsg_id.value == HubQMsgEnum.MSGQ_KILL_CNX_PLAYER.value:    
                    break
                    
            print('Exit sending thread player ' + str(self.player_id))                        
        t = Thread(target=handle)
        return t             
        
        
        
        
 
