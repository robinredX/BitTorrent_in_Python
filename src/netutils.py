def read_line(f):
    res = b''
    while True:
        b = f.recv(1)
        if len(b) == 0:
            return None
        if b == b"\n":
            break
        res += b
    return res