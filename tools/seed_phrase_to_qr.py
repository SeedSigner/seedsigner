
if __name__ == "__main__":
    import qrcode
    import sys
    from embit import bip39

    print(sys.argv)
    seed_phrase = sys.argv[1:]
    print(seed_phrase)

    data = ""
    for word in seed_phrase:
        index = bip39.WORDLIST.index(word)
        data += str("%04d" % index)

    qr = qrcode.QRCode( version=1, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=5, border=3)
    qr.add_data(data)
    qr.make(fit=True)
    qr.make_image(fill_color="black", back_color="white").resize((240,240)).convert('RGB').show()
