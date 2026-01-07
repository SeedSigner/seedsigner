# Silent Payments (BIP-352)

SeedSigner supports verifying Silent Payment transactions. This guide explains what Silent Payments are, how they work with SeedSigner, and how to use the feature.

## What are Silent Payments?

Silent Payments allow you to receive Bitcoin without revealing a reusable address on-chain. Instead of giving someone a static `bc1q...` address (which links all payments together), you share a Silent Payment address (`sp1...`) that generates a unique, unlinkable output for each transaction.

**Key benefit**: Privacy - observers cannot link multiple payments to the same recipient.

## How It Works Without SeedSigner Verification

Your wallet software (BlueWallet, Sparrow, etc.) handles Silent Payments:

1. You enter the recipient's `sp1...` address
2. Wallet derives a unique `bc1p...` Taproot output address
3. Wallet builds the transaction (PSBT)
4. You scan the PSBT into SeedSigner
5. SeedSigner shows: **"Sending 0.01 BTC to bc1p7x9y..."**
6. You approve and sign

**The problem**: You see a random-looking `bc1p...` address with no way to verify it actually corresponds to the `sp1...` address you intended to pay.

## The Risk

If your wallet software is:
- **Buggy** - it might miscalculate the output address
- **Compromised** - malware could substitute a different address
- **MITM attacked** - the PSBT could be modified in transit

You would unknowingly sign a transaction sending funds to the wrong address.

## How SeedSigner Verification Helps

With SeedSigner's Silent Payment support, you can verify the wallet did the math correctly:

1. **Scan the SP address first** - Point your SeedSigner at the `sp1...` QR code
2. SeedSigner confirms: "Silent Payment Address - Mainnet"
3. **Scan the PSBT** from your wallet
4. SeedSigner independently calculates what the output should be
5. SeedSigner verifies the PSBT output matches
6. SeedSigner shows: **"Sending 0.01 BTC to sp1qq..."** with the original address
7. You approve with confidence

## Step-by-Step Usage

### 1. Prepare the SP Address QR
Display or print the recipient's `sp1...` address as a QR code.

### 2. Scan the SP Address
- On SeedSigner: **Scan** (from main menu or with a seed loaded)
- Point camera at the SP address QR
- Confirm the address and network shown

### 3. Build the Transaction
- In your wallet (BlueWallet, Sparrow, etc.), create a transaction to the SP address
- Export as PSBT (QR code format)

### 4. Scan and Sign the PSBT
- Scan the PSBT QR into SeedSigner
- Review the transaction details
- Verify the SP address matches your intended recipient
- Approve and sign

### 5. Broadcast
- Scan the signed PSBT back into your wallet
- Broadcast to the network

## Why Can't SeedSigner Generate SP Addresses?

Unlike regular Bitcoin addresses, Silent Payment outputs are **transaction-specific**. The derived `bc1p...` address depends on:

1. Which UTXOs (coins) you're spending
2. The specific transaction inputs (txid:vout)

This means:
- Every transaction to the same `sp1...` produces a **different** `bc1p...` output
- You need to know which coins you're spending before deriving the address
- Only a wallet with UTXO knowledge can create the transaction

**SeedSigner is stateless by design** - it holds your keys but has no blockchain data or UTXO information. Therefore:
- Your wallet builds the transaction and derives the SP output
- SeedSigner verifies the derivation is correct and signs

## Supported Address Formats

| Format | Network | Example |
|--------|---------|---------|
| `sp1...` | Mainnet | `sp1qqgste7k9hx0qftg6qmwlkqtwuy6...` |
| `tsp1...` | Testnet | `tsp1qqgste7k9hx0qftg6qmwlkqtwuy6...` |

## Compatible Wallets

Silent Payment-capable coordinator wallets that work with SeedSigner:
- BlueWallet (with SP support)
- Sparrow Wallet (with SP support)
- Any wallet that exports PSBTs with SP-derived Taproot outputs

## BIP-375 Support (Automatic Verification)

SeedSigner now supports [BIP-375](https://github.com/bitcoin/bips/blob/master/bip-0375.mediawiki), which embeds SP information directly in the PSBT. When a coordinator wallet includes BIP-375 fields, SeedSigner automatically verifies the SP output using [DLEQ proofs](https://github.com/bitcoin/bips/blob/master/bip-0374.mediawiki) - no address scanning required.

**Verification priority:**

1. PSBT contains BIP-375 SP fields → Verify via DLEQ proof (automatic, no scanning needed)
2. No BIP-375 fields, but user scanned SP address → Verify via re-derivation
3. Neither → Display `bc1p...` only (no SP verification possible)

**BIP-375 PSBT Fields Supported:**

| Field                              | Type       | Description                         |
| ---------------------------------- | ---------- | ----------------------------------- |
| `PSBT_OUT_SP_V0_INFO` (0x09)       | Per-output | Contains B_scan and B_spend keys    |
| `PSBT_GLOBAL_SP_ECDH_SHARE` (0x07) | Global     | ECDH shared point for verification  |
| `PSBT_GLOBAL_SP_DLEQ` (0x08)       | Global     | 64-byte DLEQ proof                  |
| `PSBT_IN_SP_ECDH_SHARE` (0x1d)     | Per-input  | Per-input ECDH share (future)       |
| `PSBT_IN_SP_DLEQ` (0x1e)           | Per-input  | Per-input DLEQ proof (future)       |

The "scan SP address first" workflow remains valuable as:

- A fallback for coordinators that don't include BIP-375 fields
- Works with any SP-capable wallet today
- An extra layer of verification even with BIP-375 support

**Note on PSBTv2:** BIP-375 specifies these fields for PSBTv2 (BIP-370). SeedSigner uses the embit library which stores BIP-375 fields in its `unknown` dict regardless of PSBT version. This means:

- PSBTv0 with BIP-375 fields added: **Supported**
- PSBTv2 with embedded transaction: **Supported** (embit parses v2)
- Pure PSBTv2 without `PSBT_GLOBAL_UNSIGNED_TX`: May have limited support depending on embit version

Most coordinator wallets currently export v0-compatible PSBTs, so this should not be an issue in practice.

## Testing BIP-375 Verification

To test SeedSigner's BIP-375 verification without a full wallet setup, use the **BIP-375 Test PSBT Generator**:

[github.com/FreeOnlineUser/bip375-test-tools](https://github.com/FreeOnlineUser/bip375-test-tools)

This tool generates valid BIP-375 PSBTs with fake inputs for testing purposes. It includes:

- GUI with side-by-side QR codes for SP address and PSBT
- Seed QR export for loading test sender keys into SeedSigner
- Animated UR QR codes for easy PSBT scanning
- Camera scanning to verify signed PSBTs returned from SeedSigner
- Proper DLEQ proof generation per BIP-374
- Full end-to-end signing flow testing

**Note:** Test PSBTs reference non-existent inputs and cannot be broadcast to the network.

## Technical Reference

For implementation details, see:

- [BIP-352: Silent Payments](https://github.com/bitcoin/bips/blob/master/bip-0352.mediawiki)
- [BIP-375: Sending Silent Payments with PSBTs](https://github.com/bitcoin/bips/blob/master/bip-0375.mediawiki)
- [BIP-374: DLEQ Proofs](https://github.com/bitcoin/bips/blob/master/bip-0374.mediawiki)
