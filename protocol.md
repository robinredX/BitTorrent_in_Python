
# Networking protocol

![INFO](https://scontent-cdt1-1.xx.fbcdn.net/v/t1.15752-0/p480x480/51427892_841606676174634_3727167710321180672_n.png?_nc_cat=111&_nc_ht=scontent-cdt1-1.xx&oh=1944c834695820d91198385a342aff38&oe=5CF5D08A)

## 1. Definitions
1. **Stuff** (the actual data to share)
    * this can be any kind of file (video, music, ...)
    * as an extension, this could also be a set of files
    * each _stuff_ will be split into _books_

2. **Library** (“torrent file” in BitTorrent)
    * this is a description of the _stuff_ to exchange
    * it can be stored as a text file that will be shared with all _players_ (in a real case, this file could be stored on a webserver named “l411.me” that lists _library_ files)
    * the file extension .libr will be used
    * it contains the following information
        * the address of the _hub_ (e.g., 192.168.6.66:42000)
        * the name of the _stuff_
        * the size of the _stuff_
        * the size used for each _book_
        * the number of _books_ (not mandatory, this is redundant)
        * for each _book_, its SHA1

3. **Book** (“piece” in BitTorrent)
    * this represents a part of a _stuff_ to download
    * this is the unit of exchange: _players_ exchange _books_
    * _books_ are all of the same size, except the last one (if the _stuff_ size is not a multiple of the _book_ size)
    * the size of the _books_ is 16kBytes
    * SHA1
        * this is a type of checksum that we will use to check the integrity of a _book_
        * it is stored in the _library_ file
        * it is checked by the _player_ when receiving a _book_ (or when restarting with a partially downloaded _stuff_)
  
4. **Player** (“peer” in BitTorrent)
    * this is a program exchanging _books_ with others _players_
    * it first loads a _library_ file
    * it finds others _players_ by querying the _hub_
    * it remembers (in memory) the SHA1 of each _book_
    * it remembers what _books_ it has, and shares this information with other _players_
    * it can ask _books_ to other _players_
    * it can provide _books_ to other _players_

5. **Hub** (“tracker” in BitTorrent)
    * this is a program that maintains an updated list of all _players_ exchanging the _stuff_
    * it provides, on demand by a _player_, a list of other _players_ to connect to
    * it does nothing else: it does not download or upload any _book_, does not know what _player_ has what _books_, etc.

---
## 2. Initialisation

![INITIALISATION](https://scontent.xx.fbcdn.net/v/t1.15752-9/51642155_323379508283201_1806439536478126080_n.png?_nc_cat=111&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent.xx&oh=89c096cbde011213742a3323b3e4adc3&oe=5CEF61B5)

* To share a _stuff_, the _player_ selects a specific file it wants to share. After selecting the file, a _library_ file is generated using a program called the __librarifier__. This _library_ file is used by _players_ to identify the _hub_. It also define _books_ of the _stuff_. Each _stuff_ is identified in the exchange network by the SHA1 of the info field of the _library_ file.

* Initially the _hub_ starts with no registered _players_.

* After the first seeder _player_ creates the _library_ it communicates his IP address to the _hub_.

* The _hub_ registers the _player_'s IP Address, the listening port, its seeder (or leecher) status and saves it inside a dictionary of _players_.

---
## 3. Processing and Requests

![PROCESSING](https://scontent.xx.fbcdn.net/v/t1.15752-0/p480x480/50999263_241380393461495_613387773012869120_n.png?_nc_cat=100&_nc_ad=z-m&_nc_cid=0&_nc_ht=scontent.xx&oh=4874832d64ac84ba8a5e4d715b92462c&oe=5CB89D48)

1. If a _player_ wants to download a _stuff_ it requests the _hub_ to send him a dictionary of _players_. The same request can be performed periodically.

2. The _hub_ sends back a dictionary to the _player_. This dictionary contains a list of _player_ information (_player_ id, ip address, listening port, seeder status). The connection to the _hub_ is closed after receiving the message.

3. Once the _player_ receives the dictionary it starts sending a __handshaking__ request to all the other _players_ in the dictionary.  
  The other _players_ answer the handshaking with a __bitfield__ message to notify which _books_ they have.

4. The other _players_ send a __bitfield__ message to other _players_ to notify which _book_ it owns.
   
5. The _player_ sends an __interested__ or __not intersted__ message to other _players_. 
   The other _players_ sends an __interested__ or __not interested__ message to the _player_.
  
6. The _player_ can decide to choke a _player_ at any time by sending a __choking__ message. __Choking__ message means that no data will be sent until __unchoking__ happens. There can be several reasons for __choking__ e.g. the __player__ has reached its maximum upload capacity or the other __player__ does not want any pieces.

7. The _player_ sends a __request__ message to a specific number of _players_ who are interested. The __request__ message specifies which _book_ is required.

8. When a _book_ is completely received, the _player_ matches the SHA1 checksum of the _book_ to the one in the _library_ file. If its integrity is maintained, the _player_ sends a __have__ message to the seeder _player_.
   
9. From to time the _player_ can update its status to the _hub_ by sending a __hub notify__ message.

 
---
## 4. Other cases
* If the downloader _player_ can not reach some _players_ from the dictionnary sent by the _hub_, the _player_ sends a __player invalid address__ message to the _hub_. The _hub_ can check the connection to these _players_ and remove them from its dictionary if necessary.

* A _player_ can remove itself from the _hub_ dictionary by sending a __hub notify__ message whith event field value equal to 'stopped'.

*  A _player_ can send __keep_alive__ to stay connected with the other _player_ for 30 minutes.

## 5. Encoding

The messages are bencoded. Bencode can encode 4 different types:
  - byte strings,
  - integers,
  - lists, 
  - dictionaries.  
 
(source Wikipedia: https://en.wikipedia.org/wiki/Bencode)  
**An integer** is encoded as i`<integer encoded in base ten ASCII`>e. Leading zeros are not allowed (although the number zero is still represented as "0"). Negative values are encoded by prefixing the number with a hyphen-minus. The number 42 would thus be encoded as i42e, 0 as i0e, and -42 as i-42e. Negative zero is not permitted.  
**A byte string** (a sequence of bytes, not necessarily characters) is encoded as `<length`>:`<contents`>. The length is encoded in base 10, like integers, but must be non-negative (zero is allowed); the contents are just the bytes that make up the string. The string "spam" would be encoded as 4:spam. The specification does not deal with encoding of characters outside the ASCII set.
**A list** of values is encoded as l`<contents`>e . The contents consist of the bencoded elements of the list, in order, concatenated. A list consisting of the string "spam" and the number 42 would be encoded as: l4:spami42ee. Note the absence of separators between elements, and the first character is the letter 'l', not digit '1'.  
**A dictionary** is encoded as d`<contents`>e. The elements of the dictionary are encoded each key immediately followed by its value. All keys must be byte strings and must appear in lexicographical order. A dictionary that associates the values 42 and "spam" with the keys "foo" and "bar", respectively (in other words, {"bar": "spam", "foo": 42}), would be encoded as follows: d3:bar4:spam3:fooi42ee.  


## 6. Player-player communication
The following protocol is inspired by the BitTorrent protocol with some modifications (source: https://wiki.theory.org/index.php/BitTorrentSpecification#Tracker_HTTP.2FHTTPS_Protocol)

`<len=0x0001`> : 2 bytes to encode the length of the message (in the case length=1)  
`<id=0x00`> : 1 by to code the message id
#### Message definition
- **keep alive**:         `<len=0x0000`>  
- **choke**:              `<len=0x0001`>`<id=0x00`>   
- cho
- **unchoke**:            `<len=0x0001`>`<id=0x01`>    
- **interested**:         `<len=0x0001`>`<id=0x02`>
- **not interested**:     `<len=0x0001`>`<id=0x03`>  
- **have**:               `<len=0x0005`>`<id=0x04`>`<book index`>   
  The payload is the zero-based index of a _book_ that has just been successfully downloaded and verified via the hash
- **bitfield**:           `<len=0x0001+X`>`<id=0x05`>`<bitfield`>    
  - bitfield : X bytes :  The payload is a bitfield representing the _books_ that have been successfully downloaded.  
                          The high bit in the first byte corresponds to _book_ index 0. Bits that are cleared indicated a missing _book_,  
                          and set bits indicate a valid and available _book_. Spare bits at the end are set to zero.
- **request**:            `<len=0x0005`>`<id=0x06`>`<index`>
  - index : 4 bytes : index of the requested _book_  
- **book**:              `<len=0x0005+X`>`<id=0x07`>`<index`>`<payload`>  
  - index   : 4 bytes : index of the requested _book_  
  - payload : X bytes : data from _stuff_ in binary  
- **handshake**:          '<len=0x0029`>`<id=0x08><hash_info`>`<player_id`>
  - info_hash: 20 bytes : 20-byte SHA1 of the info dictionary of the _library_ file (used in _hub_ notify message)  
  - player_id: 20 bytes : 20-byte id that uniquely identifies _player_


## 7. Player-hub communication
#### Message definition

- **hub notify**:     `<len=0x0001+X`>`<id=0x10`>`<payload size=X`>   
  - payload : X bytes : bendoded dictionary composed of b'key':value (bencoded value as bytefield, integer, list or dictionary) 
      - b'info_hash': 20-byte SHA1 hash of the value of the info key from the _library_ file.  
      - b'player_id': 20-byte id that uniquely identifies _player_
      - b'port':  listening port as integer
      - b'downloaded': downloaded size (including failed part), in bytes, as integer      
      - b'uploaded' : uploaded size, in bytes, as integer 
      - b'left': left to download, in bytes, as integer
      - b'event: either b'started', b'completed', b'stopped'   (started : no _book_ received, stopped: sent when _player_ shutdown gracefully or the sender does not have the file anymore, completed: when all _book_ are received)
        
- **hub answer**:    `<len=0x0001+X`>`<id=0x11`>`<payload size=X`>  
  - payload : X bytes : bendoded dictionary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary) 
    - failure reason: If present, then no other keys may be present. The value is a human-readable error message as to why the request failed (string).
    - b'warning message': (optional) The response still gets processed normally. The warning message is shown just like an error.
    - b'interval': Interval in seconds that the _player_ should wait between sending regular requests to the _hub_
    - b'min interval': (optional) Minimum announce interval, in seconds. If present clients must not reannounce more frequently than this.
    - b'complete': number of players with the entire file, i.e. seeders (integer)
    - b'incomplete': number of non-seeder players, aka "leechers" (integer)
    - b'players': (dictionary model) The value is a list of dictionaries, each with the following keys:
       - b'player id': _player_'s self-selected ID, as described above for the _hub_ request (string)
       - b'ip': IP of the _player_
       - b'port' : listening port
       - b'complete' : 0 if _player_ doesn't have the full file, 1 if the _player_ has the full file 

- **player invalid address**:    `<len=0x0001+X`>`<id=0x12`>`<payload size=X`>  
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary b ) 
    - b'list_player': list of b'IP/port'     with IP=xxx.xxx.xxx.xxx
    Define a list of _players_ who are not reachable
    
  
## 8. Player id
The player_id is exactly 20 bytes (characters) long.
The player_id uses the following encoding: '-', two characters for client id, four ascii digits for version number, '-', followed by random numbers.
e.g. : -RO0101-[12 random bytes]

## 9. Library file format
The content of a metainfo file (the file ending in ".libr") is a bencoded dictionary, containing the keys listed below.
All character string values are UTF-8 encoded.  
  - **announce**: The announce of the hub (string) b'IP/port')   with IP=xxx.xxx.xxx.xxx
  - **creation date**: (optional) the creation time of the _library_ file, in standard UNIX epoch format (integer, seconds since 1-Jan-1970 00:00:00 UTC)
  - **created by:** (optional) name and version of the program used to create the .libr (string)
  - **info**: a dictionary that describes the stuff(s) of the _library_ file.
