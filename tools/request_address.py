if __name__ == "__main__":
    import qrcode

    derivation_path = "m/44'/148'/1'"
    data = f"request-address;{derivation_path}"

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
