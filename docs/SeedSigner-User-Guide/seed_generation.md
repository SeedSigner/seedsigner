# Generating and Managing Seed Phrases
A Bitcoin seed is the master key that generates all your Bitcoin wallet addresses. It's like a master password that can recreate your entire wallet. In SeedSigner, you have multiple methods to generate this critical piece of information.

## Generating a New Seed
1. **New Seed Creation**
   - Creates a completely new, randomly generated Bitcoin seed phrase (12 or 24 words)

![Generate Seed Menu](https://github.com/SeedSigner/seedsigner-screenshots/raw/dev/en/tools_views/ToolsMenuView.png)  
**Methods of Generating Randomness (Entropy):**
- **Dice Rolls:** The most secure method of introducing true randomness
  - **12-word seed:** Requires 50 dice rolls
  - **24-word seed:** Requires 99 dice rolls  

  - **Manual Input:** Manually input random data
- **Built-in Randomness:** Using device's internal entropy generation
   

2.  **Calculate 12th/24th Word**

  ![Generate Seed Menu](https://github.com/SeedSigner/seedsigner-screenshots/raw/dev/en/tools_views/ToolsImageEntropyMnemonicLengthView.png)  ![Generate Seed Menu](https://github.com/SeedSigner/seedsigner-screenshots/raw/dev/en/tools_views/ToolsDiceEntropyMnemonicLengthView.png)
  
- **Purpose:** Complete an existing seed phrase where you know 11 or 23 words and verify the correct final word (checksum)
- **How It Works:** Input the first 11 or 23 words; SeedSigner calculates the mathematically correct final word to ensure your seed phrase is valid and complete. 

3. **Address Explorer**
- **Functionality:** Preview addresses generated from a seed, verify seed phrase correctness, inspect different derivation paths, and check receive/change addresses.
![Generate Seed Menu](https://github.com/SeedSigner/seedsigner-screenshots/raw/dev/en/tools_views/ToolsAddressExplorerSelectSourceView.png)  
- **Use Cases:** Confirm seed phrase before backup, cross-reference with other wallets, understand address generation process.


4. **Seed Verification**
- **Verification Methods:** Cross-check seed phrase integrity, validate checksum, and ensure words are from the standard Bitcoin word list.
- **Security Checks:** Detect transcription errors, prevent accidental seed phrase mistakes, and confirm the seed phrase is mathematically valid.

---


## Backup Recommendations

* Write down seed words on paper
* Create multiple backup copies
* Store in secure, separate locations
* NEVER store digitally


**Next Step:** [Transaction Signing →](./transaction_signing.md)
