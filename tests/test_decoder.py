from lumensigner.models import DecodeQR, QRType, DecodeQRStatus


def test_decode_request_address():
    data = "request-address;m/44'/148'/100'"
    d = DecodeQR()
    d.add_data(data)
    assert d.qr_type == QRType.REQUEST_ADDRESS
    assert d.is_complete
    assert d.get_request_address_data() == 100


def test_decode_sign_hash_data():
    data = "sign-hash;m/44'/148'/1';3389e9f0f1a65f19736cacf544c2e825313e8447f569233bb8db39aa607c8889"
    d = DecodeQR()
    d.add_data(data)
    assert d.qr_type == QRType.SIGN_HASH
    assert d.is_complete
    assert d.get_sign_hash_data() == (
        1,
        "3389e9f0f1a65f19736cacf544c2e825313e8447f569233bb8db39aa607c8889",
    )


def test_decode_sign_tx_data():
    qrcodes = [
        "p1of4;sign-transaction;m/44'/148'/1';AAAAAgAAAACCfNHArCC/mgGCcbFHn9sg/f20zwTGgAZ85/lUZk/7ZwAAAGQACFT6dq",
        "p2of4;sign-transaction;90FAAAAAEAAAAAAAAAAAAAAABkfqVzAAAAAAAAAAEAAAAAAAAAAQAAAADrOSiBrkIAwb25qGY1tlTlwE",
        "p3of4;sign-transaction;5fTwf2xn8c0WcKLI450AAAAAFVU0RDAAAAAEI+fQXy7K+/7BkrIVo/G+lq7bjY5wJUq+NBPgIH3layAA",
        "p4of4;sign-transaction;AAHLCyO7gAAAAAAAAAAA==;Test SDF Network ; September 2015",
    ]

    d = DecodeQR()
    for i in qrcodes:
        if d.add_data(i) == DecodeQRStatus.COMPLETE:
            break
        assert d.qr_type == QRType.SIGN_TX
    assert d.is_complete
    address_index, te = d.get_sign_transaction_data()
    assert address_index == 1
    assert (
        te.to_xdr()
        == "AAAAAgAAAACCfNHArCC/mgGCcbFHn9sg/f20zwTGgAZ85/lUZk/7ZwAAAGQACFT6dq90FAAAAAEAAAAAAAAAAAAAAABkfqVzAAAAAAAAAAEAAAAAAAAAAQAAAADrOSiBrkIAwb25qGY1tlTlwE5fTwf2xn8c0WcKLI450AAAAAFVU0RDAAAAAEI+fQXy7K+/7BkrIVo/G+lq7bjY5wJUq+NBPgIH3layAAAAHLCyO7gAAAAAAAAAAA=="
    )
