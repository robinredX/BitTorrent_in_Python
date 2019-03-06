# 2019-net-d

#  About the project

This is a BitTorrent client written in Python. The primary objective is to provide a stable and fast way to efficiently share files between users without the loss of integrity. <br/>

The client creates a torrent file from the file to be shared. The file is then shared between different peers (regarded as players). <br/>
 
Our client identifies which users are available and which parts of the file should be downloaded first and from which player. This provides fast downloading and sharing. This BitTorrent client checks for the integrity of the file-components (regarded as books) that is being shared and thus maintaining integrity of the file. 

## Installation and requirements

Requires Python 3+
```

librarifier.py addr path book_size output # e.g. librarifier.py '127.0.0.1/6666' 'C:\\file' 0x4000 'file.libr'
hub.py
```


## Architecture of the BitTorrent Client

A brief description of interaction between different parts of the code is given below:

![Architecture](https://github.com/robinredX/ProjectBittorrent/blob/master/code_architecture.jpg)









