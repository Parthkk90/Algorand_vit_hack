# Cresca Campus - Deployment Status

## 🚀 Testnet Deployment Summary

**Network:** Algorand Testnet  
**Date:** February 12, 2026  
**Deployer:** `ZQ7ZL5WFQBVVQ5L5HBO5Q3AE4TC7DQVIEA6LDWCI7UYZLCOU3DMUF2UNZA`

---

## ✅ Deployed Smart Contracts

| Contract | App ID | Status | Explorer Link |
|----------|--------|--------|---------------|
| **Expense Splitter** | `755399831` | ✅ Deployed & Tested | [View on Explorer](https://testnet.explorer.perawallet.app/application/755399831) |
| **DAO Treasury** | `755399773` | ✅ Deployed & Tested | [View on Explorer](https://testnet.explorer.perawallet.app/application/755399773) |
| **Soulbound Ticket** | `755399774` | ✅ Deployed & Tested | [View on Explorer](https://testnet.explorer.perawallet.app/application/755399774) |
| **Fundraising Escrow** | `755399775` | ✅ Deployed & Tested | [View on Explorer](https://testnet.explorer.perawallet.app/application/755399775) |

---

## 📄 Contract Details

### 1. Expense Splitter (App ID: 755399831)

**Purpose:** Enable groups of up to 16 members to track and settle shared expenses atomically.

**Transaction History:**
- Deploy TX: `KQ2ZBMCJTH6PCJOZ3G5B2LIZ7FRY5F6QX6LHNORTIZRLAPPCZXYQ`
- Opt-in TX: `NCZYFXFBOSDKUNDLUZ2XHGOV5TQO6SK6JBLC72GSZ23CZXZAXHNQ`

**State Schema:**
- Global Ints: 5 (creator, member_count, expense_count, is_settled, total_pool)
- Global Bytes: 1
- Local Ints: 3 (net_balance, balance_sign, has_opted_in)
- Local Bytes: 0

**Current State:**
```
member_count: 1
expense_count: 0
is_settled: 0
```

---

### 2. DAO Treasury (App ID: 755399773)

**Purpose:** Multi-signature treasury contract for club fund management with M-of-N approval.

**Transaction History:**
- Deploy TX: `7P6EZF2QPYKVVZ47GA5Q5RRLQEN3VCCXN4K2V3DV2WTNQXUPRANA`
- Opt-in TX: `5WFWNJGQZEZXRZKIONMFXD3U5ICT4FXOSQSYQRXDI3XFIPUQ4FRQ`

**State Schema:**
- Global Ints: 4 (creator, threshold, signer_count, proposal_count)
- Global Bytes: 1
- Local Ints: 1 (is_signer)
- Local Bytes: 0

**Current State:**
```
threshold: 2
signer_count: 0
proposal_count: 0
```

---

### 3. Soulbound Ticket (App ID: 755399774)

**Purpose:** ARC-71 Non-Transferable Asset (NTA) implementation for event tickets that cannot be resold.

**Transaction History:**
- Deploy TX: `YWEVIBZERYYKJZGNTHXNSP632CGSJNVLN7K4D4SMW4RT3X4XCCUA`
- Create Event TX: `W5Y5AR4N2POTBIDUNFJABOOYFLMLSNKCRM5JXWU75GQN623W4EAQ`

**State Schema:**
- Global Ints: 1 (event_count)
- Global Bytes: 0
- Local Ints: 0
- Local Bytes: 0

**Current State:**
```
event_count: 1
```

**Test Event Created:** Event ID 1 was successfully created during testing.

---

### 4. Fundraising Escrow (App ID: 755399775)

**Purpose:** Transparent crowdfunding with milestone-based fund release and automatic refunds.

**Transaction History:**
- Deploy TX: `G6MYZKNNLPWKTE7Q233UQKRDO2F2UKCHFANG226EDWQSVXIHMPAQ`
- Create Campaign TX: `ZD2VVT3HY5HZ7F4RD73S6Y2MSTGZQLKW3ARAIHF53V7E5SEFWSBA`

**State Schema:**
- Global Ints: 1 (campaign_count)
- Global Bytes: 0
- Local Ints: 0
- Local Bytes: 0

**Current State:**
```
campaign_count: 1
```

**Test Campaign Created:** Campaign ID 1 was successfully created during testing.

---

## 💰 Deployment Costs

| Action | Cost (ALGO) |
|--------|-------------|
| Deploy Expense Splitter | ~0.001 |
| Deploy DAO Treasury | ~0.001 |
| Deploy Soulbound Ticket | ~0.001 |
| Deploy Fundraising | ~0.001 |
| Test Transactions | ~0.004 |
| **Total Cost** | **~0.008 ALGO** |

**Initial Balance:** 10.0000 ALGO  
**Final Balance:** 9.9920 ALGO  
**Total Spent:** 0.0080 ALGO

---

## 🔧 Environment Configuration

Add these to your `.env` file:

```env
# Algorand Testnet Configuration
ALGOD_SERVER=https://testnet-api.algonode.cloud
ALGOD_TOKEN=
INDEXER_SERVER=https://testnet-idx.algonode.cloud
NETWORK=testnet

# Deployed Contract App IDs
EXPENSE_SPLITTER_APP_ID=755399831
DAO_TREASURY_APP_ID=755399773
SOULBOUND_TICKET_APP_ID=755399774
FUNDRAISING_APP_ID=755399775
```

---

## 🧪 Test Results

All contracts were tested successfully on testnet:

```
============================================================
🏫 CRESCA CAMPUS - CONTRACT TESTING
============================================================

📍 Network: Algorand Testnet
💰 Balance: 9.9960 ALGO

✅ Expense Splitter tests passed!
✅ DAO Treasury tests passed!
✅ Soulbound Ticket tests passed!
✅ Fundraising tests passed!

🎉 ALL TESTS COMPLETED!

💰 Final Balance: 9.9920 ALGO
💸 Test Cost: 0.0040 ALGO
```

---

## 📁 Build Artifacts

Compiled TEAL files are located in the `build/` directory:

```
build/
├── expense_splitter_approval.teal
├── expense_splitter_clear.teal
├── dao_treasury_approval.teal
├── dao_treasury_clear.teal
├── soulbound_ticket_approval.teal
├── soulbound_ticket_clear.teal
├── fundraising_approval.teal
└── fundraising_clear.teal
```

---

## 🔗 Useful Links

- **Algorand Testnet Explorer:** https://testnet.explorer.perawallet.app
- **Testnet Dispenser:** https://bank.testnet.algorand.network/
- **AlgoNode API Docs:** https://algonode.io/api/

---

## 📝 Next Steps

1. **Frontend Integration:** Connect React/Next.js frontend to deployed contracts
2. **Wallet Integration:** Integrate Pera Wallet with Liquid Auth
3. **Fee Pooling:** Set up sponsor wallet for gasless onboarding
4. **Additional Testing:** Run full end-to-end tests with multiple users
5. **Mainnet Deployment:** After thorough testing, deploy to mainnet

---

## 🏆 Hackathon Track

**Track 1: Future of Finance**

This deployment demonstrates:
- ✅ Smart contract development on Algorand
- ✅ ARC-71 Soulbound NFT implementation
- ✅ Multi-sig DAO treasury
- ✅ Milestone-based escrow fundraising
- ✅ Atomic expense settlement

---

*Last Updated: February 12, 2026*
