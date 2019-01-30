## Encoding

The message are bencoded. Bencode can encode 4 different types:
  - byte strings,
  - integers,
  - lists, 
  - dictionaries.  
 
(source Wikipedia)  
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




The foolowing protocol is inspired by bitTorrent protocole with some modifications (source: https://wiki.theory.org/index.php/BitTorrentSpecification#Tracker_HTTP.2FHTTPS_Protocol)
## Player-player communication
#### Message definition

- **keep alive**:         `<len=0x0000`>  
- **choke**:              `<len=0x0001`><`id=0x00`>    
- **unchoke**:            `<len=0x0001`><`id=0x01`>    
- **interested**:         `<len=0x0001`><`id=0x02`>
- **not interested**:     `<len=0x0001`><`id=0x03`>  
- **have**:               `<len=0x0005`><`id=0x04`>`<book index`>   
  The payload is the zero-based index of a book that has just been successfully downloaded and verified via the hash
- **bitfield**:           `<len=0x0001+X`>`<id=0x05`>`<bitfield`>    
  - bitfield : X bytes :  The payload is a bitfield representing the books that have been successfully downloaded.  
                          The high bit in the first byte corresponds to book index 0. Bits that are cleared indicated a missing book,  
                          and set bits indicate a valid and available book. Spare bits at the end are set to zero.
- **request**:            `<len=0x0009`>`<id=0x06`>`<index`>
  - index : 8 bytes : index of the requested book  
- **book**:              `<len=0x0009+X`>`<id=0x07`>`<index`>`<payload`>  
  - index   : 8 bytes : index of the requested piece  
  - payload : X bytes : data from stuff in binary  
- **cancel**:             `<len=0x0009`>`<id=0x08`>`<index`>  
  Cancel request for the book matching index number 
- **handshake**:          '<len=0x29`>`<id=0x09><hash_info`>`<peer_id`>
  - info_hash: 20 bytes : 20-byte SHA1 of the info dictionnary of the torrent file (used in tracker notify message)  
  - peer_id: 20 bytes : 20-byte id that uniquely identify peer


## Player-hub communication
#### Message definition

- **hub notify**:     `<len=0x0001+X`>`<id=0x10`>`<payload size=X`>   
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary) 
      - b'info_hash': 20-byte SHA1 hash of the value of the info key from the Metainfo file.  
      - b'peer_id': 20-byte id that uniquely identify peer
      - b'port':  listening port as integer
      - b'downloaded': downloaded size (including failed part) as integer      
      - b'uploaded' : uploaded size as integer 
      - b'left': left to download as integer
      - b'event: either b'started', b'completed', b'stopped'   (started : no piece received, stopped: sent when player shutdown gracefylly,
        completed: when all pieces are received)
        
- **hub answer**:    `<len=0x0001+X`>`<id=0x12`>`<payload size=X`>  
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary) 
    - failure reason: If present, then no other keys may be present. The value is a human-readable error message as to why the request failed (string).
    - warning message: (optional) The response still gets processed normally. The warning message is shown just like an error.
    - interval: Interval in seconds that the client should wait between sending regular requests to the tracker
    - min interval: (optional) Minimum announce interval. If present clients must not reannounce more frequently than this.
    - complete: number of peers with the entire file, i.e. seeders (integer)
    - incomplete: number of non-seeder peers, aka "leechers" (integer)
    - peers: (dictionary model) The value is a list of dictionaries, each with the following keys:
    - peer id: peer's self-selected ID, as described above for the tracker request (string)

- **player invalid IP**:    `<len=0x0001+X`>`<id=0x13`>`<payload size=X`>  
  - payload : X bytes : bendoded dictionnary composed of b'key':value (bencoded value as bytefield, integer, list or dictionnary b ) 
    - b'list_peer': list of b'IP/port'     with IP=xxx.xxx.xxx.xxx


## Library file format
The content of a metainfo file (the file ending in ".libr") is a bencoded dictionary, containing the keys listed below.
All character string values are UTF-8 encoded.  
  - **announce**: The announce of the hub (string) b'IP/port')   with IP=xxx.xxx.xxx.xxx
  - **creation date**: (optional) the creation time of the library file, in standard UNIX epoch format (integer, seconds since 1-Jan-1970 00:00:00 UTC)
  - **created by:** (optional) name and version of the program used to create the .libr (string)
  - **info**: a dictionary that describes the stuff(s) of the library file.




