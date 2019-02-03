"""
Libraryfier module

Generate .libr file

usage : libraryfier.py addr path book_size output

e.g. libraryfier.py '127.0.0.1/6666' 'C:\\file' 0x4000 'file.libr'

"""
from hashlib import sha1
import os, math, sys, time
import string
from bencode import bencode, bdecode



class MetainfoFile:
    """Create a Metainfo file"""
    def __init__(self, announce: str, file_path: str, piece_length: int):
        # Metainfo
        self._get_date()
        if os.path.exists(file_path) == True:
            self.piece_length = piece_length
            self.file_path = file_path
            self._file_size = os.path.getsize(file_path)
            self._nb_pieces = math.ceil(self._file_size/self.piece_length)
            #print(self._nb_pieces)        
        else:
            print("File path does not exist")
            sys.exit(-1)
        
        self.announce = announce
        if '\\' in self.file_path:
            self._file_name = file_path.split('\\')[-1] 
        else:
            self._file_name = file_path
  
        self._metafile = []
        self._hashes = 0    
            
    def get_metafile(self):
        metainfo_dict = {}
        metainfo_dict[b'announce'] = bytes(self.announce, 'utf-8')
        metainfo_dict[b'created by'] = b'RoZaLaEd v1.0.0'
        metainfo_dict[b'creation date'] = self._get_date()
        metainfo_dict[b'info']={}
        metainfo_dict[b'info'][b'length'] = self._file_size
        metainfo_dict[b'info'][b'name'] = bytes(self._file_name, 'utf-8')
        metainfo_dict[b'info'][b'piece length'] = self.piece_length
        metainfo_dict[b'info'][b'pieces'] = b''

        with open(self.file_path,'rb') as f:          
            read_size = 0
            while read_size < self._file_size :
                segment = f.read(self.piece_length)
                read_size += self.piece_length
                hash_code = self._compute_signature(segment)
                metainfo_dict[b'info'][b'pieces'] += hash_code
        f.close()
        #print(metainfo_dict)
        
        metainfo = bencode(metainfo_dict)
        return(metainfo)
        
    def _get_date(self):
        date = int(time.time())
        return date
    
    def _compute_signature(self, segment):    
        piece_hash = sha1(segment).digest()
        return piece_hash


if __name__ == '__main__':
    addr = sys.argv[1]
    path = sys.argv[2]
    book_size = int(sys.argv[3],0)
    output  = sys.argv[4]
    metainfo_file = MetainfoFile(addr, path, book_size)
    metainfo = metainfo_file.get_metafile()
    
    f = open(output,'wb')
    f.write(metainfo)
    f.close()
