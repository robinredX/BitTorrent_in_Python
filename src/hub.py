from threading import Thread
import binascii
import socket
import queue
import os
from netutils import read_line
import numpy as np

import message #from laetitia (bug fixed)
import utils #from laetitia

# DONE answers requests from players over TCP as bencoded message + bytes("\n", "utf-8") and disconnects the socket; 
# TODO consider having three main queues. is there an andvantage?
# 1. listening
# 2. processing (because maybe if there's a gazillion libr files and players, and the choice process is complicated, 
# processing takes a lot of time and will get in the way)
# 3. sending back
# TODO handling timeouts
# 1. as requests arrive, {player_id: timestamp} is sent to "blocked players" queue, *if not already there*,
# otherwise ignored;
# 2. consumer thread checks the head of the "blocked players" queue timestamp and deletes player if timeout has passed
# TODO periodically save player records to file
# TODO over http??
# TODO change library dictionary to {libr_ID:{seeders:{player1:{ip:xxxxxx, port:xxxx}, player2:{...}}, leechers:{}}},
# if I want to have some sort of preferential serving for seeders
# TODO figure out something useful to do with "down" and "up" from notify messages
# TODO what can be done with the "remain" return?
# 1. send "incomplete messages" to a matching queue and... what's the idea?
# 2. Wouldn't it be in the spirit of distributed architectures to just ignore incomplete messages and put the 
# onus on the players to make the request again?
# TODO checking reported players ideas
# 1. using the HandshakeMsg with random player_ID/or reporting player ID; the idea is simulate a normal request
# 2. have a specific handshake for the hub; maybe not so good, since could be exploited by malicious players
# TODO warning should include no seeds, maybe average time from leecher to seed



def main():
    library = Library()
    at_this_port = 7776
    q =  queue.Queue()
    
    listen(q, at_this_port).start()
    speak(q, library).start()


def listen(q,at_this_port):
    """Accepts incoming player connection at_this_port; processess each request on a 
        separate thread """
    def handle():
        hub_socket = socket.socket()
        hub_socket.bind(('localhost', at_this_port))
        hub_socket.listen()
        print("Waiting for connection")
        while True:
            player_socket, player_addr = hub_socket.accept()
            print("Received connection at: ", player_socket)
            queue_up_player_message(player_socket, player_addr, q).start()
    t = Thread(target=handle)
    return t

def queue_up_player_message(socket, player_addr, q):
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

def speak(q, library):
    """Takes stuff from the queue, identifies it, processess it and either processes it or queues up the action"""
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
                        # close connection
                        print("ACTION: closing socket...", socket)
                        socket.close()
                        print("REPORT: printing dictionary...", library.lib)
                    elif message_type == 'player invalid address':
                        # check reported players
                        print("ACTION: checking reported players...")
                        confirmed = check_reported_players(objMsg)
                        # remove players from dictionay
                        print("ACTION: removing "+str(len(confirmed))+ " players from dictionary...")
                        library.remove_player_list(library.lib, confirmed)
                        # close connection
                        print("ACTION: closing socket...", socket)
                        socket.close()
                    else:
                        pass
                else:
                    print("ERROR: message couuuuurruoo###3upttttted!")
            except:
                print("ERROR: not really a message :", e[1])

    t = Thread(target=handle)
    return t

class Library(object):
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
            print("something is wrong!")
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
    
def check_reported_players(decoded_msg):
    return []


if __name__== "__main__":
  main()