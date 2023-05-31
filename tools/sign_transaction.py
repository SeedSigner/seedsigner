import time

if __name__ == "__main__":
    import qrcode

    derivation_path = "m/44'/148'/1'"
    network_passphrase = "Test SDF Network ; September 2015"
    transaction_xdr = "AAAAAgAAAACCfNHArCC/mgGCcbFHn9sg/f20zwTGgAZ85/lUZk/7ZwAAAGQAEnw5AAAAAQAAAAEAAAAAAAAAAAAAAABkcrMxAAAAAAAAAAEAAAAAAAAAAQAAAABzbWS8nBkx9MNaVshYHFQbixEkTLpv6X9hCFFs8CIn/QAAAAAAAAAAO5rKAAAAAAAAAAAA"

    command = "sign-transaction"
    data = f"{derivation_path};{transaction_xdr};{network_passphrase}"
    data_piece_length = 64
    data_pieces = [
        data[i : i + data_piece_length] for i in range(0, len(data), data_piece_length)
    ]
    total_pieces = len(data_pieces)
    while True:
        for i, data_piece in enumerate(data_pieces):
            data_piece = f"p{i + 1}of{total_pieces};{command};{data_piece}"
            print(data_piece)
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=5,
                border=3,
            )
            qr.add_data(data_piece)
            qr.make(fit=True)
            qr.make_image(fill_color="black", back_color="white").resize(
                (240, 240)
            ).convert("RGB").show()
            time.sleep(1)
