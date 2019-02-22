from queue import Queue
import hubplayer
import hublibrary

def main():
    this_IP = 'localhost'
    at_this_port = 7777
    hub_address = (this_IP, at_this_port)

    queue =  Queue()
    hub_library = hublibrary.HubLibrary()
    hub_to_player = hubplayer.HubPlayer(hub_address)
    
    hub_to_player.listen(queue).start()
    hub_to_player.speak(queue, hub_library).start()

if __name__== "__main__":
  main()