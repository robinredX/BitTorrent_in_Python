import socket
import message
import utils
from threading import Thread
from netutils import read_line

def main():
    s = socket.create_connection(('localhost', 7776))
    print(s)
    # listen before you speak!
    listen(s).start()
    speak(s, "report").start()

def speak(s, type_of_request):
    def handle():
        while True:
            type_of_request = input()
            if type_of_request == "notify":
                player_id = utils.generate_player_id()
                metainfo = utils.Metainfo("new.libr")
                msg = message.HubNotifyMsg(metainfo.get_info_hash(), player_id, 7777, 0x8000, 0x4000, 65255558, b'start').msg_encode()
                bytes_l = msg
            elif type_of_request == "report":
                invalid_players = [b'192.123.128.213/3366',b'148.253.125.32/6658',b'155.63.25.32/2356',b'126.35.98.36/8521', b'126.35.98.31/8599']
                msg = message.PlayerInvalidAddrMsg(invalid_players).msg_encode()
                bytes_l = msg
            else:
                bytes_l = bytes(type_of_request, 'utf-8')
            try:
                k = s.sendall(bytes_l + bytes("\n", 'utf-8'))
            except:
                print("disconnected, can't speak")
                break
    return Thread(target = handle)

def listen(s):
    def handle():
        people_are_speaking = True
        while people_are_speaking:
            try:
                l = read_line(s)
                if l is None:
                    break
                print("RECEIVED:", l)
            except:
                print("diconnected, can't listen")
    return Thread(target=handle)

if __name__== "__main__":
  main()