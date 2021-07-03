# Developer Tips

### Quickly generate a new seed to test with
Generate a new 12- or 24-word seed via [https://iancoleman.io/bip39/](https://iancoleman.io/bip39/).

Access a `python3` environment that has the `embit` library installed (e.g. your own local machine, ssh into the SeedSigner, etc)

Start a python REPL session by just typing: `python3`

Paste in the following but insert your newly generated mnemonic:
```
from embit import bip39
seed_phrase = "smoke chimney announce candy glory tongue refuse fatigue cricket once consider beef treat urge wing deny gym robot tobacco adult problem priority wheat diagram"
data = ""
for word in seed_phrase.split(" "):
    index = bip39.WORDLIST.index(word)
    data += "%04d" % index

print(data)
```

For the seed in the snippet, you should see:
```
163803200074026607961827144306700411123603780160185419152013046908321497181700301371136719990487
```

Take the output and paste it into a [QR code generator](https://www.the-qrcode-generator.com/).

Start up SeedSigner's UI to import a seed from a QR code. Scan the new QR code and you're good to go!
