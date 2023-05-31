if __name__ == "__main__":
    import qrcode

    derivation_path = "m/44'/148'/1'"
    transaction_hash = (
        "1113f23c225495534b2fd589a037798155ea73ee68a418e74364c1a3be4a20d8"
    )
    data = f"sign-hash;{derivation_path};{transaction_hash}"

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=5,
        border=3,
    )
    qr.add_data(data)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").resize((240, 240)).convert(
        "RGB"
    ).show()
