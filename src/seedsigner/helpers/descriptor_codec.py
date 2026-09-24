import enum
from embit import base58
from embit.descriptor import Descriptor

class Tag(enum.IntEnum):
    """
    Maps Miniscript AST operators and primitive structure definitions to their
    associated binary prefix tags defined in the Josh Doman Compressed Descriptor spec.
    """
    Sh = 0x03
    Wpkh = 0x04
    Wsh = 0x05
    Tr = 0x06
    SortedMulti = 0x09
    Multi = 0x19
    Origin = 0x24
    NoOrigin = 0x25
    CompressedFullKey = 0x27
    XPub = 0x29

class ByteStream:
    """
    A lightweight stateful iterative byte reader.
    Keeps track of cursor position while recursively digesting template and payload bytes
    without copying or slicing arrays.
    """
    def __init__(self, data: bytes):
        self.data = data
        self.cursor = 0

    def read(self, n: int) -> bytes:
        chunk = self.data[self.cursor : self.cursor + n]
        self.cursor += n
        return chunk
    
    def read_u8(self) -> int:
        return self.read(1)[0]
    
    def eof(self) -> bool:
        return self.cursor >= len(self.data)

def decode_varint(stream: ByteStream) -> int:
    """
    Decodes an unsigned Variable-Length Integer (LEB128).
    This format is used by the algorithm to compress threshold lengths,
    key counts (n, k), and derivation path numbers.
    """
    result = 0
    shift = 0
    while True:
        byte = stream.read_u8()
        result |= (byte & 0x7f) << shift
        if not (byte & 0x80):
            break
        shift += 7
    return result

class DescriptorDecoder:
    """
    A recursive abstract syntax tree parser that transforms bounded bytes 
    into Miniscript string notation. It processes Template bytes structurally
    and shifts Payload bytes based on predefined element sizes.
    """
    def __init__(self, template: bytes, payload: bytes):
        self.tpl = ByteStream(template)
        self.pld = ByteStream(payload)
    
    def decode_miniscript(self) -> str:
        """
        Recursively constructs the highest-level Miniscript statements
        (wsh, sh) and handles threshold structures (multi, sortedmulti).
        """
        tag = self.tpl.read_u8()
        
        if tag == Tag.Sh:
            return f"sh({self.decode_miniscript()})"
        elif tag == Tag.Wpkh:
            return f"wpkh({self.decode_key()})"
        elif tag == Tag.Wsh:
            return f"wsh({self.decode_miniscript()})"
        elif tag == Tag.SortedMulti or tag == Tag.Multi:
            k = decode_varint(self.tpl)
            n = decode_varint(self.tpl)
            keys = [self.decode_key() for _ in range(n)]
            op = "sortedmulti" if tag == Tag.SortedMulti else "multi"
            return f"{op}({k},{','.join(keys)})"
        
        raise ValueError(f"Unsupported Miniscript tag: {hex(tag)}")
        
    def decode_key(self) -> str:
        """
        Parses Key primitives (compressed keys and extended pubkeys).
        Requires matching Key tags followed immediately by an Origin designation.
        """
        tag = self.tpl.read_u8()

        if tag == Tag.CompressedFullKey:
            origin = self.decode_origin()
            key_hex = self.pld.read(33).hex()
            if origin:
                return f"[{origin}]{key_hex}"
            return key_hex
            
        elif tag == Tag.XPub:
            origin = self.decode_origin()
            # Xpubs are encoded as 78 bytes in the payload. We Base58Check encode it here
            raw_xpub = self.pld.read(78)
            key_b58 = base58.b58encode_check(raw_xpub).decode('ascii')
            
            if origin:
                return f"[{origin}]{key_b58}"
            return key_b58
            
        raise ValueError(f"Unsupported Key tag: {hex(tag)}")

    def decode_origin(self) -> str:
        """
        Extracts key origins, mapping the Fingerprint and building the BIP32 path string
        using the LEB128 decoded depths and integer mappings (2c+1 for hardened).
        """
        tag = self.tpl.read_u8()
        if tag == Tag.NoOrigin:
            return ""
        elif tag == Tag.Origin:
            fingerprint = self.pld.read(4).hex()
            path_len = decode_varint(self.tpl)
            paths = []
            for _ in range(path_len):
                child_num = decode_varint(self.tpl)
                if child_num % 2 != 0:
                    paths.append(f"{(child_num - 1) // 2}'")
                else:
                    paths.append(f"{child_num // 2}")
            path_str = "/".join(paths)
            return f"{fingerprint}/{path_str}" if path_str else fingerprint
            
        raise ValueError(f"Expected Origin tag, got: {hex(tag)}")


def decode_compressed_descriptor(payload_bytes: bytes, template_len: int) -> str:

    template = payload_bytes[:template_len]
    payload = payload_bytes[template_len:]
    
    decoder = DescriptorDecoder(template, payload)
    
    try:
        desc_str = decoder.decode_miniscript()
        desc = Descriptor.from_string(desc_str)
        return str(desc) 
    except Exception as e:
        return desc_str
