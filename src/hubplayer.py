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

import message
import utils

class HubPlayer(object):
    def __init__(self, address):
            self.timed_out_players = []
            self.hub_socket = socket.socket()
            self.hub_socket.bind(address)
            self.hub_socket.listen()
            print("Waiting for connection")
            #time-out defaults to 10 seconds for testing purposes,
            #and only checks the IP
            #this makes more sense than playerID, since the latter is self-generated
            #and makes more sense than checking the port also, since we could be 
            #spamming the hub from multiple client instances on the same machine
            #TODO make sure it matches the hub answer interval

    def listen(self, q):
        def handle():
            while True:
                player_socket, player_addr = self.hub_socket.accept()
                self.update_timed_out(time_out= 10)
                #akward as hell, but it works
                #TODO make it nicer, maybe start with an nparray already
                #but then appending creates a shallow copy, which I then have to 
                #point the original object at... Help?! 
                blocked_players = np.asarray(self.timed_out_players)
                try:
                    test = player_addr[0] in blocked_players[:,1]
                except:
                    test = False
                if test:
                    print("Received connection attempt from blocked player! Ignoring it...")
                    player_socket.close()
                    #TODO Send a message to the player spamming the hub with the remaining time
                else:
                    print("Received connection at: ", player_socket)
                    self.timed_out_players.append((time.time(), player_addr[0]))
                    self.queue_up_player_message(player_socket, player_addr, q).start()
        t = Thread(target=handle)
        return t

    def speak(self, q, library):
        def handle():
            while True:
                e = q.get()
                socket = e[0]
                player_addr = e[1]
                msg = e[2]
                try: 
                    status, remain, objMsg = message.ComMessage.msg_decode(msg)
                    message_type = objMsg.get_message_type()
                    print("MESSAGE TYPE :", message_type)
                    if status == 0:
                        if message_type == 'hub notify':
                            # update dictionary information
                            print("ACTION: updating dictionary info...")
                            requires_reply = library.update_dictionary_info(objMsg, player_addr)
                            # send player list
                            if requires_reply:
                                print("ACTION: sending back player list...")
                                library.send_player_list(socket, objMsg, player_addr)
                            # # close connection
                            # print("ACTION: closing socket...", socket)
                            # socket.close()
                            print("REPORT: printing dictionary...", library.lib)
                        elif message_type == 'player invalid address':
                            # check reported players
                            print("ACTION: checking reported players...")
                            confirmed = []#check_reported_players(objMsg)
                            # remove players from dictionay
                            print("ACTION: removing "+str(len(confirmed))+ " players from dictionary...")
                            library.remove_player_list(library.lib, confirmed)
                            # # close connection
                            # print("ACTION: closing socket...", socket)
                            # socket.close()
                        else:
                            pass
                    else:
                        print("ERROR: message couuuuurruoo###3upttttted!")
                except:
                    print("ERROR: not really a message :", e[1])
        t = Thread(target=handle)
        return t

    def queue_up_player_message(self, socket, player_addr, q):
        """Reads message arriving at a socket, puts it in the queue"""
        def handle():
            while True:
                try: # if can't read because player disconnected
                    msg = read_line(socket)
                except:
                    break # then get out of the loop
                if msg is None:
                    break
                else:
                    q.put((socket, player_addr, msg))
        t = Thread(target=handle)
        return t

    def update_timed_out(self, time_out = 50):
        #TODO Make it a bit more efficient by not having to check the entire list; since it's added in 
        # order, once enough time has passed
        new_time = time.time() 
        self.timed_out_players = [x for x in self.timed_out_players if new_time-x[0] < time_out]
