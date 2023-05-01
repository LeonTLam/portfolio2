def parse_flags(flags):
    #we only parse the first 3 fields because we're not 
    #using rst in our implementation
        syn = flags & (1 << 3)
        ack = flags & (1 << 2)
        fin = flags & (1 << 1)
        res = flags & (1 << 0)
        return syn, ack, fin, res

flags = 12

flags = parse_flags(flags)
print(f"{flags[1]}")

def test(noe, noe1, noe2):
    if noe:
        print(1)
    elif noe1:
        print(2)
    elif noe2:
        print(3)

test(None, True, None)