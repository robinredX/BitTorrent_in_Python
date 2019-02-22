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

import message
import utils

class HubLibrary(object):
    def __init__(self):
        self.lib = {}

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
            print("EVENT: start")
            try:
                self.lib[lib_file][player] = {"ip": address[0], "port": address[1], "complete": int(0 == left)}
            except:
                self.lib[lib_file] = {}
                self.lib[lib_file][player] = {"ip": address[0], "port": address[1], "complete": int(0 == left)}
            requires_reply = 1

        elif event == b'stopped':
            print("EVENT: stopped")
            try:
                del self.lib[lib_file][player]
            except:
                print("IGNORED: no such library/player")
        elif event == b'completed':
            print("EVENT: completed")
            if 0 == left:
                self.lib[lib_file][player]["seed"] = {int(0 == left)}

        else:
            print("ERROR: something is wrong!")
        print(self.lib)
        return requires_reply

    def remove_player_list(self, lib_file, players):
        #TODO consider removing from all lib_files, since connection is down
        for player in players:
            try:
                del self.lib[lib_file][player]
            except:
                print("IGNORED: no such library/player")

    def send_player_list(self, socket, lib_file, address, number_requested = 50):
        lib_ID = lib_file.get_info_hash()
        seeder_number = 1
        leecher_number = 1
        players = np.random.choice(list(self.lib[lib_ID].keys()),size = min(len(self.lib[lib_ID]), number_requested), replace = False)
        to_send = []
        for player in players:
            to_send += {'player_id': player, 'ip':self.lib[lib_ID][player]["ip"], 'port':self.lib[lib_ID][player]["port"], 'complete':self.lib[lib_ID][player]["complete"]},
        if len(players)!=0:
            msg = message.HubAnswerMsg(b'', b'', 100, 5, seeder_number, leecher_number, to_send).msg_encode()
            print(socket.sendall(msg+bytes("\n", 'utf-8')))
        else:
            print("no players")
        # TODO: player should not be served in the list of players
        # TODO: warnings should be about player availability, seeder availability...?
        # TODO: seeder and leecher number should come from the dictionary
   