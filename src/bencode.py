"""
bencode module

bencode and decode messages

"""

def bencode(item) -> bytes:
    """ Bencoding of an object.
    Exception: TypeError is raised when item type does not match any of the 4 expected types
    """
    
    if isinstance(item, int):
        return b"i%ie" % item
    elif isinstance(item, dict):
        return b"d%se" % b"".join([_bencode_dict(k, v) for k, v in sorted(item.items())])
    elif isinstance(item, list):
        return b"l%se" % b"".join(map(bencode, item))
    elif isinstance(item, bytes):
        return b"%i:%s" % (len(item), item)

    raise TypeError("Invalid type (item must be an integer, a dictionary, a list or a bytestring )")
                        
  
    
def bdecode(msg) -> bytes:   
    info_dict, sub = _bdecode_subcode(msg)
    return info_dict
    
    
def _bdecode_subcode(c: bytes):
    if len(c)<2:
        raise ValueError("Error")

    if c[0:1] == b'i':
        l, sub = c.split(b'e',1)
        byte_integer = int(l[1:])
        return byte_integer, sub
        
    elif c[0:1] == b'l':
        list = []
        sub = c[1:]
        while sub[0:1] != b'e':
            item, sub = _bdecode_subcode(sub)
            list.append(item)
        return list, sub[1:]
        
    elif c[0:1] == b'd':
        info_dict = {}
        sub = c[1:]
        while sub[0:1] != b'e':
            key,sub = _bdecode_subcode(sub)
            #print(key)
            value, sub = _bdecode_subcode(sub)
            #print(value)            
            info_dict[key] = value
        return info_dict, sub[1:]
        
    else:
        l, sub = c.split(b':',1)
        
        #print(int(l))
        byte_item = sub[0:int(l)]
        #print(byte_item)
        return byte_item, sub[int(l):]

 
def _bencode_dict(key: bytes, value):
    if isinstance(key, bytes):
        return bencode(key) + bencode(value)
        
    raise TypeError("Invalid type (key must be a bytestring)")
    
