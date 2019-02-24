import sys, socket
from queue import Queue
from hubplayer import HubPlayer
from hublibrary import HubLibrary 

def main():
    this_IP = 'localhost'
    at_this_port = 8001
    hub_address = (this_IP, at_this_port)
    
    hub_library = HubLibrary()
    lib_queue = hub_library.get_library_queue()
    
    # Start server socket allowing player connection
    while True:
        try :
            server_socket = socket.socket()
            server_socket.bind((this_IP, at_this_port))
            server_socket.listen() 
            break
        except:
            print('Cannot connect hub. Terminate.')
            sys.exit(-1)
            
                
    print('Hub is connected')
    print("Waiting for connection")    
    # Wait for player connection
    while True:       
        socket_client, addr = server_socket.accept()   
        print("Received connection", socket_client)            
        client = HubPlayer(socket_client, addr, lib_queue)    
    
    
if __name__== "__main__":
  main()
