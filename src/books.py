import os
import math
from hashlib import sha1
from utils import Metainfo


class Books(object):
    def __init__(self, full_path: str, metafile: Metainfo):
        self.full_path = full_path
        self.download_path, self.file_name = os.path.split(os.path.abspath(full_path))
        self.books = dict()
        self.metafile = metafile
        bytes_size = int(math.ceil(metafile.get_book_number() / 8))

        self.bitfield = bytearray(bytes_size)
        print(full_path)
        if os.path.isfile(full_path):
            with open(full_path, 'rb') as file:
                for book_index in range(self.metafile.get_book_number()):
                    piece_data = file.read(self.metafile._book_length)
                    piece_hash = sha1(piece_data).digest()

                    if piece_hash == self.metafile.get_book_hash(book_index):
                        self.add_index(book_index)
        else:
            print('Create file')
            print(full_path)
            with open(full_path, "wb") as file:
                file.truncate(self.metafile.get_stuff_size())
                
    def get_bitfield(self):
        return self.bitfield

    def add_index(self, book_index):
        byte_index = book_index // 8
        bit_index = book_index % 8
        shift_index = 8 - (bit_index + 1)
        byte_mask = 1 << shift_index

        self.bitfield[byte_index] |= byte_mask


    def remove_index(self, book_index):
        byte_index = book_index // 8
        bit_index = book_index % 8
        shift_index = 8 - (bit_index + 1)
        byte_mask = ~(1 << shift_index)

        self.bitfield[byte_index] &= byte_mask


    def missing_books(self):
        missing = []
        for i in range(self.metafile.get_book_number()):
            if not self.have_book(i):
                missing.append(i)

        return missing


    def existing_books(self):
        existing = []
        for i in range(self.metafile.get_book_number()):
            if self.have_book(i):
                existing.append(i)
        return existing

    def get_downloaded_stuff_size(self):
        nb_book = len(self.existing_books())
        return nb_book * self.metafile.get_book_length()
    
    
    def have_book(self, book_index):
        byte_index = book_index // 8
        bit_index = book_index % 8
        shift_index = 8 - (bit_index + 1)

        return (self.bitfield[byte_index] >> shift_index) & 1


    def read_book(self, book_index):
        try:
            with open(self.full_path, 'rb') as file:
                file.seek(book_index * self.metafile.get_book_length())
                book_data = file.read(self.metafile.get_book_length())
            return book_data

        except IOError:
            print('I/O Error in read book %d', book_index)
            return None


    def write_book(self, book_index, data):
        try:
            with open(self.full_path, 'r+b') as file:
                file.seek(book_index * self.metafile.get_book_length())
                file.write(data)
                self.add_index(book_index)
            return True

        except IOError:
            print('I/O Error in write book %d', book_index)
            return False

if __name__ == '__main__':
    meta_file = Metainfo('file.libr')
    new_file = Books("D:\\Work\\UJM\\Semester 2\\Computer Networking\\Project\\test2.mkv", meta_file)
    new_file_2 = Books("D:\\Work\\UJM\\Semester 2\\Computer Networking\\Project\\test3.mkv", meta_file)

    # print('Bitfield: ' + str(new_file.bitfield))
    # print(new_file.existing_books())
    # print(new_file.missing_books())
    #
    # new_file.remove_index(31)
    # print('--------------------------------------------------------')
    # print('Bitfield: ' + str(new_file.bitfield))
    # print(new_file.existing_books())
    # print(new_file.missing_books())
    #
    # new_file.add_index(31)
    # print('--------------------------------------------------------')
    # print('Bitfield: ' + str(new_file.bitfield))
    # print(new_file.existing_books())
    # print(new_file.missing_books())

    print(new_file_2.bitfield)

    for i in range(meta_file.get_book_number()):
        data = new_file.read_book(i)
        new_file_2.write_book(i, data)

    print(new_file_2.bitfield)
