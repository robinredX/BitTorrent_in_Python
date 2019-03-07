# 2019-net-d

#  About the project

This is a Peer to Peer client written in Python. The primary objective is to provide a stable and fast way to efficiently share files between users without the loss of integrity. <br/>

The client creates a torrent file from the file to be shared. The file is then shared between different peers (regarded as players). <br/>
 
Our client identifies which users are available and which parts of the file should be downloaded first and from which player. This provides fast downloading and sharing. This BitTorrent client checks for the integrity of the file-components (regarded as books) that is being shared and thus maintaining integrity of the file. 

The Hub is maintaining a list of players that is supplied after registration of the player.

## Installation and requirements

### Requirement: 
Python 3.6+  

### Setup :  
1 - Create the library file: 
```
librarifier.py addr path book_size output # e.g. librarifier.py '127.0.0.1/6666' 'C:\\Stuff_file' 0x4000 'file.libr'
addr format: 'IP/PORT'
```
2 - Create a root directory (root_dir) to store the stuff.

3 - Prepare the environnement for the 1st player that owns the complete stuff. For this, we run player.py.
   To start the player, it is necessary to input different parameters:
   - a root directory where the stuff is going to be deposit.
   - the path for the library file
   - the client_id that we be set to __None__ for the first run.
   e.g. player.py D:\Torrent D:\Torrent\library.libr None 
   
   The program can be shot down as soon as it tries to connect to the Hub
 
 4 - A directory has been newly created by player.py under the root directory. The name of the directory identifies the player_id.
 Keep memory of the player_id.
 Put the stuff in the newly created directory.
 
 5 - Start the hub. There are no parameters
 ```
hub.py 
```  

6 - Start the first player using the player_id obtained in step 4 as a third parameter
```   
player.py root_dir library_file player_id
e.g. player.py D:\Torrent D:\Torrent library.libr -RO0101-7ec7150dddf3      
```   

7 - Other players can be started with the same command with player id as None or existing player_id in the root_dir.
When a player is started with an existing player_id, the stuff file present in the player directory will keep updating.
At start, the player examines the file and detect the existing books by computing SHA1 on chunk of the file and comparing it to the ones stored in the library file.

With Windows operating system, for convenience, it is possible to create batch file (.bat) containing the starting command. Then the program can be started with a double clic on the batch file.
To start a new player (example of content for a batch file):
```   
python.exe player.py root_dir library_file None
pause
```
To restart an existing player:
``` 
python.exe player.py root_dir library_file player_id     
pause
```  


Note that the listening port number of the player is selected randomly. The availability of the port is checked at the beginning, if the port is not free another one is picked.

The process allows running multiple players on the same machine even on a local host.


## Code Architecture of the BitTorrent Client

A brief description of interaction between different parts of the code is given below:

![Interaction between different parts of code](https://github.com/robinredX/ProjectBittorrent/blob/master/code_interaction.jpg)

The hub application accepts inbound communication from players. It creates a new instance of HubPlayer for each new connection. This object manages 2 threads that deal with receiving and sending messages via the socket.

A instance of HubCommunication object manages the exchange with the Hub. It notified the PlayerConnectionManager of new events by sending messages in the PlayerConnectionManager queue.

PlayerConnectionManager oversees inbound and outbound connections. It keeps interacting with the HubCommunication and all other connection objets through its queue which is read in a dedicated thread.  

For inbound connection, other players connect to the player server, which is know by advertising of the Hub.
For each new connection, an instance of PlayerCommunicationClient is created, dealing with 2 threads and a queue: 1 thread is listening to the input of the socket, the second thread is waiting for message in the queue, thus receiving instructiong from the listening thread or the PlayerConnectionManager for sending messages via the socket. PlayerCommunicationClient can send notification to PlayerConnectionManager using its queue.

For oubound connection, the connection is initiated by PlayerConnectionManager after reception of the list of player from the HubCommunication. For each connected player, an instance of PlayerCommunicationServer is created. It is build on the same model as the 
PlayerCommunicationClient.

Resources are managed by 2 object instances: the Book that deals with the stuff file access and the HubLibrary that deals with the list of players in the Hub. Each object manages a thread that listen to incoming queue messages to fulfill request, so that it can manage concurential access.





