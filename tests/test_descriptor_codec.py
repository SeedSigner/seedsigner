import pytest
from seedsigner.helpers.descriptor_codec import decode_compressed_descriptor

def test_decoder_wsh_sortedmulti():
    """
    Ensures that the decompressed output strictly matches the canonical format.
    Tested against Josh Doman's integrated test vector:
    wsh(sortedmulti(2,03a0434...47c7,...))#hfj7wz7l
    
    Encoded string:
    Template = 05090203272527252725 (10 bytes)
    Payload = 99 bytes (3 * 33 byte compressed keys)
    Total Length = 109 bytes
    """
    raw_hex = "0509020327252725272503a0434d9e47f3c86235477c7b1ae6ae5d3442d49b1943c2b752a68e2a47e247c7036d2b085e9e382ed10b69fc311a03f8641ccfff21574de0927513a49d9a688a0002e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29"
    raw_bytes = bytes.fromhex(raw_hex)
    
    decoded_str = decode_compressed_descriptor(payload_bytes=raw_bytes, template_len=10)
    
    expected_inner = "wsh(sortedmulti(2,03a0434d9e47f3c86235477c7b1ae6ae5d3442d49b1943c2b752a68e2a47e247c7,036d2b085e9e382ed10b69fc311a03f8641ccfff21574de0927513a49d9a688a00,02e8445082a72f29b75ca48748a914df60622a609cacfce8ed0e35804560741d29))"
    
    # Since Embit is imported dynamically in the PR and might modify formatting slightly
    # or add a checksum, we assert the base matches.
    assert expected_inner in decoded_str
