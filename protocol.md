
# Networking protocol

![INFO](https://scontent-cdt1-1.xx.fbcdn.net/v/t1.15752-0/p480x480/51427892_841606676174634_3727167710321180672_n.png?_nc_cat=111&_nc_ht=scontent-cdt1-1.xx&oh=1944c834695820d91198385a342aff38&oe=5CF5D08A)

## 1. Definitions
1. Stuff (the actual data to share)
    * this can be any kind of file (video, music, ...)
    * as an extension, this could also be a set of files
    * each stuff will be split into books

2. Library (“torrent file” in BitTorrent)
    * this is a description of the stuff to exchange
    * it can be stored as a text file that will be shared to all players (in a real case, this file could be stored on a webserver named “l411.me” that lists library files)
    * the file extension .libr will be used
    * it contains the following informations
        * the address of the hub (e.g., 192.168.6.66:42000)
        * the name of the stuff
        * 
        * the size of the stuff
        * the size used for books
        * the number of books (not mandatory, this is redundant)
        * for each book, its SHA1

3. Book (“piece” in BitTorrent)
    * this represents a part of a stuff to download
    * this is the unit of exchange: players exchange books
    * books are all of the same size, except the last one (if the stuff size is not a multiple of the book size)
    * the size of the books is 16kBytes
    * SHA1
        * this is a type of checksum that we will use to check the integrity of a book
        * it is stored in the library file
        * it is checked by the player when receiving a book (or when restarting with from a partially downloaded stuff)
  
4. Player (“peer” in BitTorrent)
    * this is a program exchanging books with others players
    * it first loads a library file
    * it finds others players by querying the hub
    * it remembers (in memory) the SHA1 of each book
    * it remembers what book it has, and shares this information with others players
    * it can ask books to other players
    * it can provide books to other players

5. Hub (“tracker” in BitTorrent)
    * this is a program that maintains an updated list of all players exchanging the stuff
    * it provides, on demand by a player, a list of other players to connect to
    * it does nothing else: it does not download or upload any book, does not know what player has what books, etc.

---
## 2. Initialisations

![INITIALISATION](https://scontent.xx.fbcdn.net/v/t1.15752-9/51642155_323379508283201_1806439536478126080_n.png?_nc_cat=111&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent.xx&oh=89c096cbde011213742a3323b3e4adc3&oe=5CEF61B5)

* To share a stuff, the player select a specific file it want to share. After selecting the file, the librarifier create a __library__ file. This library file is used by players to identify the Hub, it also define books of the stuff. Each stuff is identified in the exchange network by the SHA1 of the info field of the library file.

* Initially the Hub starts with no registered players.

* After the first seeder player creates the __library__ it communicates his IP address to the Hub.

* The Hub registers the IP Address, the listening port, the seeder (or leecher status) and saves it inside a Dictionary of players.

---
## 3. Processing and Requests

![PROCESSING](https://scontent.xx.fbcdn.net/v/t1.15752-0/p480x480/50999263_241380393461495_613387773012869120_n.png?_nc_cat=100&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent.xx&oh=4874832d64ac84ba8a5e4d715b92462c&oe=5CB89D48)

1. If a player wants to download a stuff it requests the Hub to send him a dictionary of players. The same request can be performed periodically.

2. The Hub sends back a dictionary to the Player, the Dictionary contains a list of player information (player id, ip address, listening port, seeder status).  The connection to the hub is closed after receiving the message.

3. Once the Player receives the Dictionary it start sending a __handshaking__ request to all the other players in the dictionary.  
  The other players answer the handshaking with a __bitfield__ message to notify which books they have.

4. The other players send a __bitfield__ message to other players to notify which book it owns.
   
5. The player sends an __interested__ or __not intersted__ message to other players. 
   The other players sends an __interested__ or __not interested__ message to the play.
  
6. The player can decide to choke a player at any time by sending a __choking__ message.

7. The player send a __request__ message to a specific number of players who are interested. The __request__ message specifies which book is required.

8. When a book is completely received the player matches the SHA1 checksum of the book to the one in the library file. If the integrity is correct, the player sends a __have__ message to the seeder player.
   
9. From to time the player can update its status to the hub by sending a __hub notify__ message.

 
---
## 4. Other cases
* If the downloader player can not reach some players from the dictionnary sent by the hub, the player send a __player invalid address__ message to the hub. The hub can check the connection to these players and remove them from its dictionnary if necessary.

* A player can remover itself the the hub dictionnary by sending a __hub notify__ message whith event field value equql to 'stopped'.

*  a player can send __keep_alive__ to stay connected with the other player 30 minutes.

## 5. Encoding

The message are bencoded. Bencode can encode 4 different types:
  - byte strings,
  - integers,
  - lists, 
  - dictionaries.  
 
(source Wikipedia: https://en.wikipedia.org/wiki/Bencode)  
**An integer** is encoded as i`<integer encoded in base ten ASCII`>e. Leading zeros are not allowed (although the number zero is 
still represented as "0"). Negative values are encoded by prefixing the number with a hyphen-minus. The number 42 would thus be 
encoded as i42e, 0 as i0e, and -42 as i-42e. Negative zero is not permitted.  
**A byte string** (a sequence of bytes, not necessarily characters) is encoded as `<length`>:`<contents`>. The length is encoded 
in base 10, like integers, but must be non-negative (zero is allowed); the contents are just the bytes that make up the string. The string "spam" would be encoded as 4:spam. The specification does not deal with encoding of characters outside the ASCII set; to mitigate this, some BitTorrent applications explicitly communicate the encoding (most commonly UTF-8) in various non-standard ways. This is identical to how netstrings work, except that netstrings additionally append a comma suffix after the byte sequence.  
**A list** of values is encoded as l`<contents`>e . The contents consist of the bencoded elements of the list, in order, concatenated.
A list consisting of the string "spam" and the number 42 would be encoded as: l4:spami42ee. Note the absence of separators between
elements, and the first character is the letter 'l', not digit '1'.  
**A dictionary** is encoded as d`<contents`>e. The elements of the dictionary are encoded each key immediately followed by its value.
All keys must be byte strings and must appear in lexicographical order. A dictionary that associates the values 42 and "spam" with
the keys "foo" and "bar", respectively (in other words, {"bar": "spam", "foo": 42}), would be encoded as follows: d3:bar4:spam3:fooi42ee.  


## 6. Player-player communication
The foolowing protocol is inspired by bitTorrent protocole with some modifications (source: https://wiki.theory.org/index.php/BitTorrentSpecification#Tracker_HTTP.2FHTTPS_Protocol)

`<len=0x0001`> : 2 bytes to encode the length of the message (in the case length=1)  
`<id=0x00`> : 1 by to code the message id
#### Message definition
- **keep alive**:         `<len=0x0000`>  
- **choke**:              `<len=0x0001`>`<id=0x00`>    
- **unchoke**:            `<len=0x0001`>`<id=0x01`>    
- **interested**:         `<len=0x0001`>`<id=0x02`>
- **not interested**:     `<len=0x0001`>`<id=0x03`>  
- **have**:               `<len=0x0005`>`<id=0x04`>`<book index`>   
  The payload is the zero-based index of a book that has just been successfully downloaded and verified via the hash
- **bitfield**:           `<len=0x0001+X`>`<id=0x05`>`<bitfield`>    
  - bitfield : X bytes :  The payload is a bitfield representing the books that have been successfully downloaded.  
                          The high bit in the first byte corresponds to book index 0. Bits that are cleared indicated a missing book,  
                          and set bits indicate a valid and available book. Spare bits at the end are set to zero.
- **request**:            `<len=0x0005`>`<id=0x06`>`<index`>
  - index : 4 bytes : index of the requested book  
- **book**:              `<len=0x0005+X`>`<id=0x07`>`<index`>`<payload`>  
  - index   : 4 bytes : index of the requested book  
  - payload : X bytes : data from stuff in binary  
- **handshake**:          '<len=0x0029`>`<id=0x08><hash_info`>`<player_id`>
  - info_hash: 20 bytes : 20-byte SHA1 of the info dictionnary of the library file (used in hub notify message)  
  - player_id: 20 bytes : 20-byte id that uniquely identify player


## 7. Player-hub communication
#### Message definition

- **hub notify**:     `<len=0x0001+X`>`<id=0x10`>`<payload size=X`>   
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary) 
      - b'info_hash': 20-byte SHA1 hash of the value of the info key from the Metainfo file.  
      - b'player_id': 20-byte id that uniquely identify player
      - b'port':  listening port as integer
      - b'downloaded': downloaded size (including failed part) as integer      
      - b'uploaded' : uploaded size as integer 
      - b'left': left to download as integer
      - b'event: either b'started', b'completed', b'stopped'   (started : no book received, stopped: sent when player shutdown gracefully or the sender does not have the file anymore, completed: when all book are received)
        
- **hub answer**:    `<len=0x0001+X`>`<id=0x11`>`<payload size=X`>  
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary) 
    - failure reason: If present, then no other keys may be present. The value is a human-readable error message as to why the request failed (string).
    - b'warning message': (optional) The response still gets processed normally. The warning message is shown just like an error.
    - b'interval': Interval in seconds that the player should wait between sending regular requests to the hub
    - b'min interval': (optional) Minimum announce interval. If present clients must not reannounce more frequently than this.
    - b'complete': number of players with the entire file, i.e. seeders (integer)
    - b'incomplete': number of non-seeder players, aka "leechers" (integer)
    - b'players': (dictionary model) The value is a list of dictionaries, each with the following keys:
       - b'player id': player's self-selected ID, as described above for the hub request (string)
       - b'ip': IP of the player
       - b'port' : listening port
       - b'complete' : 0 if player doesn't have the full file, 1 if the player has the full file 

- **player invalid address**:    `<len=0x0001+X`>`<id=0x12`>`<payload size=X`>  
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary b ) 
    - b'list_player': list of b'IP/port'     with IP=xxx.xxx.xxx.xxx
    Define a list of player who are not reachable
    
  
## 8. Player id
The player_id is exactly 20 bytes (characters) long.
The player_id uses the following encoding: '-', two characters for client id, four ascii digits for version number, '-', followed by random numbers.
e.g. : -RO0101-[12 random bytes]

## 9. Library file format
The content of a metainfo file (the file ending in ".libr") is a bencoded dictionary, containing the keys listed below.
All character string values are UTF-8 encoded.  
  - **announce**: The announce of the hub (string) b'IP/port')   with IP=xxx.xxx.xxx.xxx
  - **creation date**: (optional) the creation time of the library file, in standard UNIX epoch format (integer, seconds since 1-Jan-1970 00:00:00 UTC)
  - **created by:** (optional) name and version of the program used to create the .libr (string)
  - **info**: a dictionary that describes the stuff(s) of the library file.
