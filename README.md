# Cresca Campus 🎓

> **Decentralized Campus Finance Built on Algorand**  
> Peer payments, smart splits, soulbound tickets, DAO treasuries, transparent fundraising, and fee-sponsored onboarding.  
> *No bank. No middlemen. No friction.*

[![Algorand](https://img.shields.io/badge/Algorand-Powered-blue?logo=algorand)](https://algorand.com)
[![AlgoKit](https://img.shields.io/badge/AlgoKit-3.0+-green)](https://developer.algorand.org/algokit/)
[![Track](https://img.shields.io/badge/Track%201-Future%20of%20Finance-orange)]()
[![License](https://img.shields.io/badge/License-MIT-lightgrey)](LICENSE)

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Smart Contracts](#smart-contracts)
- [Getting Started](#getting-started)
- [Development Roadmap](#development-roadmap)
- [Demo Flow](#demo-flow)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Cresca Campus** is a decentralized finance platform designed specifically for college campuses. It leverages Algorand's unique capabilities—instant finality, native atomic transactions, soulbound NFTs, and fee pooling—to solve real problems students face every day:

- Splitting bills among hostel mates
- Managing club treasuries transparently
- Buying event tickets without scalpers
- Running transparent fundraising campaigns
- Onboarding students with zero crypto experience

### Why Algorand?

| Campus Need | Traditional Pain | Algorand's Native Solution |
|-------------|------------------|---------------------------|
| P2P Payments | UPI downtime, T+1 settlement | 0.001 ALGO fee, 2.85s finality |
| Expense Splitting | Trust disputes, no atomicity | Atomic Groups: 16 txns succeed or all fail |
| Club Treasury | One person holds bank access | AVM multi-sig: no single key controls funds |
| Event Tickets | Fake tickets, scalping | ARC-71 Soulbound: protocol-enforced non-transfer |
| Fundraising | Organizers disappear with funds | Escrow with milestone-based release |
| Student Onboarding | Seed phrases, gas confusion | Fee Pooling + Liquid Auth passkeys |

---

## Features

### ⚡ 1. P2P Campus Payments (Core)
- **ALGO transfers** via simple QR scan
- Wallet = Identity (no phone numbers, no sign-up forms)
- **~$0.0003 per transaction** (0.001 ALGO fixed fee)
- 2.85-second finality, never reverts

**Algorand Primitive:** `PaymentTxn` + ASA Transfer

### 🔀 2. Smart Expense Splitting (Core)
- Create split contracts with member list
- On-chain state tracks who paid what
- "Settle All" via **Atomic Transfer** — up to 16 members settle in one block
- Disputes impossible: blockchain is the source of truth

**Algorand Primitive:** AVM App + Atomic Group (up to 16 txns)

### 🏦 3. Club DAO Treasury (Power)
- Multi-sig smart contract wallet (M-of-N approval)
- Spending proposals visible to all members on-chain
- Funds move only after on-chain approval
- Transparent history — no trust required

**Algorand Primitive:** AVM App + LogicSig

### 🎟️ 4. Soulbound Event Tickets (WOW Factor)
- Each ticket = **ARC-71 Non-Transferable ASA**
- Freeze address prevents secondary sale at protocol level
- QR scan → on-chain wallet verification at event gate
- Clawback enables revocation (no-show refunds)

**Algorand Primitive:** ARC-71 NTA + ARC-69 On-chain Metadata

### 📣 5. Transparent Campaign Fundraising (Power)
- Smart contract escrow — nobody holds the money
- Milestone-based release: funds unlock only when goals are met
- All donations visible on-chain with donor address + amount
- Auto-refund if campaign fails (contract-enforced)
- **Anonymous donor mode** via note-field encryption

**Algorand Primitive:** AVM App + Escrow Pattern + Inner Transactions

### 🎁 Bonus: Gasless Onboarding
- **Atomic Fee Pooling**: App sponsors first transactions
- **Liquid Auth** (Pera Wallet): Passkey login, no seed phrase
- New students transact on day one with zero crypto knowledge

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                           │
│                    (React / Next.js + TailwindCSS)              │
├─────────────────────────────────────────────────────────────────┤
│                     WALLET & AUTH LAYER                         │
│              Pera Wallet + Liquid Auth + use-wallet v4          │
├─────────────────────────────────────────────────────────────────┤
│                    APPLICATION LAYER                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌───────────┐ │
│  │   P2P Pay   │ │ Expense     │ │    DAO      │ │ Soulbound │ │
│  │   Contract  │ │ Splitter    │ │  Treasury   │ │  Tickets  │ │
│  └─────────────┘ └─────────────┘ └─────────────┘ └───────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │              Fundraising Escrow Contract                    ││
│  └─────────────────────────────────────────────────────────────┘│
├─────────────────────────────────────────────────────────────────┤
│                     ALGORAND LAYER                              │
│         Testnet/Mainnet • Indexer v2 • AlgoKit 3.x             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Blockchain** | Algorand Testnet → Mainnet | L1 with instant finality |
| **Smart Contracts** | Python + AlgoKit 3.x | ARC-4 ABI compliant contracts |
| **Contract Framework** | Puya (Algorand Python) | Modern Algorand development |
| **Frontend** | Next.js 14 + React 18 | Server-side rendering, fast UX |
| **Styling** | TailwindCSS + shadcn/ui | Clean, responsive UI |
| **Wallet** | Pera Wallet + Liquid Auth | Passkey login, no seed phrase |
| **Wallet Connector** | use-wallet v4 | Multi-wallet abstraction |
| **NFT Standard** | ARC-71 (Soulbound) | Non-transferable tickets |
| **Metadata** | ARC-69 | On-chain ticket metadata |
| **Indexing** | Algorand Indexer v2 | Transaction history (free) |
| **Fee Sponsorship** | Atomic Fee Pooling | Gasless onboarding |
| **Deployment** | AlgoKit deploy | One-command deploys |

---

## Project Structure

```
crescacam/
├── README.md
├── .algokit.toml                    # AlgoKit project config
├── .env.example                     # Environment template
│
├── contracts/                       # Smart contracts (Python/Puya)
│   ├── __init__.py
│   ├── p2p_payment/                 # P2P payment utilities
│   │   ├── __init__.py
│   │   └── contract.py
│   │
│   ├── expense_splitter/            # Expense splitting contract
│   │   ├── __init__.py
│   │   └── contract.py
│   │
│   ├── dao_treasury/                # DAO multi-sig treasury
│   │   ├── __init__.py
│   │   └── contract.py
│   │
│   ├── soulbound_ticket/            # ARC-71 soulbound NFT tickets
│   │   ├── __init__.py
│   │   └── contract.py
│   │
│   └── fundraising/                 # Escrow fundraising contract
│       ├── __init__.py
│       └── contract.py
│
├── tests/                           # Contract tests
│   ├── __init__.py
│   ├── test_expense_splitter.py
│   ├── test_dao_treasury.py
│   ├── test_soulbound_ticket.py
│   └── test_fundraising.py
│
├── frontend/                        # Next.js frontend
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.js
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── payments/
│   │   ├── splits/
│   │   ├── treasury/
│   │   ├── tickets/
│   │   └── fundraising/
│   ├── components/
│   │   ├── ui/
│   │   ├── wallet/
│   │   ├── qr/
│   │   └── shared/
│   ├── lib/
│   │   ├── algorand.ts
│   │   ├── contracts.ts
│   │   └── utils.ts
│   └── hooks/
│       ├── useWallet.ts
│       └── useContracts.ts
│
├── scripts/                         # Deployment & utility scripts
│   ├── deploy.py
│   ├── fund_sponsor.py
│   └── mint_test_tickets.py
│
└── docs/                            # Additional documentation
    ├── API.md
    ├── CONTRACTS.md
    └── DEPLOYMENT.md
```

---

## Smart Contracts

### 1. Expense Splitter (`contracts/expense_splitter/contract.py`)

**State Schema:**
- Global: `creator`, `total_members`, `total_expenses`, `settled`
- Local: `balance_owed`, `has_paid`

**Methods:**
- `create_split(members: list[Address])` — Initialize split group
- `add_expense(payer: Address, amount: uint64, description: bytes)` — Log expense
- `get_balance(member: Address) -> int64` — Check what member owes/is owed
- `settle_all()` — Execute atomic settlement (up to 16 members)

### 2. DAO Treasury (`contracts/dao_treasury/contract.py`)

**State Schema:**
- Global: `threshold`, `total_signers`, `proposal_count`
- Box: Proposals, Signer list

**Methods:**
- `initialize(signers: list[Address], threshold: uint64)` — Setup M-of-N
- `create_proposal(recipient: Address, amount: uint64, description: bytes)` — Propose spend
- `approve(proposal_id: uint64)` — Sign proposal
- `execute(proposal_id: uint64)` — Release funds if threshold met

### 3. Soulbound Ticket (`contracts/soulbound_ticket/contract.py`)

**ARC-71 Implementation:**
- ASA with `freeze_address` = contract address
- Metadata follows ARC-69 standard

**Methods:**
- `create_event(name: bytes, max_tickets: uint64, price: uint64)` — Create event
- `mint_ticket(buyer: Address)` — Mint frozen NFT to buyer
- `verify_ticket(holder: Address, ticket_id: uint64) -> bool` — Gate verification
- `revoke_ticket(ticket_id: uint64)` — Clawback for refunds

### 4. Fundraising Escrow (`contracts/fundraising/contract.py`)

**State Schema:**
- Global: `beneficiary`, `goal`, `deadline`, `raised`, `milestone_count`
- Box: Milestones, Donations

**Methods:**
- `create_campaign(beneficiary: Address, goal: uint64, deadline: uint64)` — Start campaign
- `donate(amount: uint64, anonymous: bool)` — Contribute to escrow
- `add_milestone(description: bytes, amount: uint64)` — Define release milestone
- `complete_milestone(milestone_id: uint64)` — Mark milestone complete
- `release_funds(milestone_id: uint64)` — Beneficiary claim via inner txn
- `refund()` — Claim refund if campaign failed

---

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 18+
- [AlgoKit CLI](https://developer.algorand.org/docs/get-started/algokit/) 3.x
- [Pera Wallet](https://perawallet.app/) (mobile or web)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/crescacam.git
cd crescacam

# Install AlgoKit and start local network
algokit localnet start

# Install Python dependencies
cd contracts
python -m venv .venv
.venv\Scripts\activate     # Windows
pip install -r requirements.txt

# Build and deploy contracts
algokit project run build
algokit project run deploy

# Install frontend dependencies
cd ../frontend
npm install

# Start development server
npm run dev
```

### Environment Variables

```env
# .env.local (frontend)
NEXT_PUBLIC_ALGOD_SERVER=http://localhost:4001
NEXT_PUBLIC_ALGOD_TOKEN=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
NEXT_PUBLIC_INDEXER_SERVER=http://localhost:8980
NEXT_PUBLIC_NETWORK=localnet

# Sponsor wallet for fee pooling
SPONSOR_MNEMONIC="your 25 word mnemonic here"
```

---

## Development Roadmap

### Phase 1: Foundation (Days 1-2) ✅
- [x] Project scaffolding with AlgoKit 3.x
- [x] README and documentation
- [ ] Base contract templates
- [ ] Local development environment

### Phase 2: Core Contracts (Days 3-5)
- [ ] **Expense Splitter** — Create, add expenses, atomic settle
- [ ] **DAO Treasury** — Multi-sig with proposal system
- [ ] Contract unit tests with AlgoKit testing

### Phase 3: Soulbound Tickets (Days 6-7)
- [ ] **ARC-71 implementation** — Freeze/clawback mechanics
- [ ] **ARC-69 metadata** — Event details on-chain
- [ ] Minting and verification flows

### Phase 4: Fundraising Escrow (Days 8-9)
- [ ] **Escrow contract** — Milestone-based release
- [ ] **Inner transactions** — Automated fund distribution
- [ ] Anonymous donor mode (note encryption)

### Phase 5: Frontend (Days 10-14)
- [ ] Next.js project setup
- [ ] Wallet connection (Pera + Liquid Auth)
- [ ] Payment & QR components
- [ ] Split management UI
- [ ] Treasury dashboard
- [ ] Ticket minting & verification
- [ ] Fundraising campaign pages

### Phase 6: Integration & Polish (Days 15-17)
- [ ] Fee pooling for onboarding
- [ ] End-to-end testing
- [ ] Mobile responsiveness
- [ ] Error handling & edge cases

### Phase 7: Demo Preparation (Days 18-20)
- [ ] Demo script rehearsal
- [ ] Testnet deployment
- [ ] Video recording
- [ ] Pitch deck finalization

---

## Demo Flow

### 3-Minute Demo Script

1. **Onboarding (30s)**  
   New student scans QR → wallet created with passkey → first transaction sponsored via fee pooling → confirmed in 2.85s

2. **Expense Split (45s)**  
   5 friends create hostel trip split → add expenses → "Settle All" → all 5 payments execute atomically in one block

3. **DAO Treasury (45s)**  
   Tech club proposes equipment purchase → 2 members approve on-chain → funds released automatically

4. **Soulbound Ticket (30s)**  
   Student buys fest ticket → NFT minted → **attempts transfer to friend → REJECTED** (frozen) → show non-transferability in Pera

5. **Fundraising (30s)**  
   Medical campaign with escrow → friends donate → milestone met → funds released via inner transaction → toggle anonymous mode

---

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Please ensure all smart contracts have corresponding tests and follow the ARC-4 ABI standard.

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

- [Algorand Foundation](https://algorand.foundation/) — For the hackathon opportunity
- [AlgoKit](https://developer.algorand.org/algokit/) — Modern Algorand development
- [Pera Wallet](https://perawallet.app/) — Liquid Auth passkeys
- VIT Campus — Real-world inspiration

---

<div align="center">

**Built for Algorand Track 1: Future of Finance**

*Cresca Campus — Finance for students, by students, on-chain.*

</div>
