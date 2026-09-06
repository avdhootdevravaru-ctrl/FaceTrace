# FaceTrace — Face Identity & Blockchain Verification Pipeline

> **Reverse-Image Discovery + Biometric Verification + Cryptographic Evidence + Blockchain Timestamping**

FaceTrace is a local CLI-based verification pipeline that proves a face in an image corresponds to a real, dynamically-discovered social-media post, then anchors the evidence to a blockchain for tamper-evident timestamping.

---

## ⚠️ Important Disclaimer

FaceTrace is an **evidence-anchoring tool**, not an identity-verification service. The pipeline produces a cryptographic commitment to a verification result, but it does **not** prove that a face belongs to a particular named individual, nor that a social-media account is owned by that person. Blockchain provides **integrity** and a **timestamp**, not truth.

---

## 📋 Table of Contents

1. [Quick Start](#quick-start)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Blockchain Configuration](#blockchain-configuration)
5. [Reverse Image Search Setup](#reverse-image-search-setup)
6. [How to Run](#how-to-run)
7. [Verification](#verification)
8. [Known Limitations](#known-limitations)

---

## 🚀 Quick Start

### Option A: Hardhat Local (Recommended for Demo)

**No MetaMask, no wallet, no POL needed.**

```powershell
# 1. Install dependencies
cd blockchain
npm install

# 2. Start local blockchain (keep running)
npx hardhat node

# 3. Deploy contract (in new terminal)
cd blockchain
npx hardhat run scripts/deploy.js --network localhost
# Copy the contract address

# 4. Configure .env
BLOCKCHAIN_MODE=hardhat
RPC_URL=http://127.0.0.1:8545
HARDHAT_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
CONTRACT_ADDRESS=<DEPLOYED_ADDRESS>

# 5. Run FaceTrace
python run.py --image examples/lena.jpg
```

### Option B: Polygon Amoy (Production Testnet)

**Requires MetaMask, wallet, and test MATIC.**

```powershell
# Configure .env
BLOCKCHAIN_MODE=polygon
RPC_URL=https://rpc-amoy.polygon.technology
PRIVATE_KEY=<YOUR_WALLET_PRIVATE_KEY>
CONTRACT_ADDRESS=<DEPLOYED_ADDRESS>

# Run FaceTrace
python run.py --image examples/lena.jpg
```

---

## 🏗️ Architecture

```
                    ┌─────────────────┐
                    │   Input Image   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Face Detection  │
                    │  (InsightFace)  │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Face Encoding   │
                    │   (ArcFace)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Reverse Image   │
                    │     Search      │
                    │   (SerpAPI)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Social Media    │
                    │   Filtering     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Candidate     │
                    │  Verification   │
                    │  (Cosine Sim)   │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │    Evidence     │
                    │      JSON       │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   SHA-256       │
                    │   Hash          │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │   Blockchain    │
                    │  Transaction    │
                    │   (Hardhat)     │
                    └────────┬────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │  Verification   │
                    └─────────────────┘
```

---

## 🛠️ Technology Stack

| Layer | Technology |
|-------|------------|
| **Programming** | Python 3.8+ |
| **Face Detection** | InsightFace / RetinaFace |
| **Face Recognition** | ArcFace |
| **Image Processing** | OpenCV, Pillow |
| **Reverse Image Search** | SerpAPI (Google Lens) |
| **Cryptographic Hash** | SHA-256 |
| **Blockchain (Local)** | Hardhat |
| **Blockchain (Public)** | Polygon Amoy |
| **Blockchain Interface** | Web3.py |
| **Smart Contract** | Solidity 0.8.19+ |
| **Configuration** | python-dotenv |
| **Interface** | CLI |

---

## ⛓️ Blockchain Configuration

FaceTrace supports two blockchain backends via the `BLOCKCHAIN_MODE` environment variable.

### Hardhat Local (Default)

Best for: Demos, testing, offline use

| Setting | Value |
|---------|-------|
| RPC URL | `http://127.0.0.1:8545` |
| Chain ID | `31337` |
| Private Key | `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` |
| Balance | 10000 ETH |

**Setup:**

```powershell
# 1. Start Hardhat node
cd blockchain
npx hardhat node

# 2. Deploy contract (new terminal)
cd blockchain
npx hardhat run scripts/deploy.js --network localhost

# 3. Configure .env
BLOCKCHAIN_MODE=hardhat
RPC_URL=http://127.0.0.1:8545
HARDHAT_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
CONTRACT_ADDRESS=<DEPLOYED_ADDRESS>
```

### Polygon Amoy

Best for: Public testnet verification

| Setting | Value |
|---------|-------|
| RPC URL | `https://rpc-amoy.polygon.technology` |
| Chain ID | `80002` |
| Currency | MATIC |

**Setup:**

1. Install MetaMask
2. Add Polygon Amoy (Chain ID: 80002)
3. Get test MATIC: https://faucet.polygon.technology/
4. Export private key
5. Deploy contract via Remix

```powershell
# Configure .env
BLOCKCHAIN_MODE=polygon
RPC_URL=https://rpc-amoy.polygon.technology
PRIVATE_KEY=<YOUR_PRIVATE_KEY>
CONTRACT_ADDRESS=<DEPLOYED_ADDRESS>
```

---

## 🔍 Reverse Image Search Setup

**Required for real reverse-image search.** Get a free key at https://serpapi.com/

```env
SERPAPI_KEY=your_api_key_here
```

Without this, the pipeline cannot perform genuine reverse image search.

---

## 🚀 How to Run

### Full Pipeline

```powershell
python run.py --image examples/lena.jpg
```

### Skip Blockchain (Local Evidence Only)

```powershell
python run.py --image examples/lena.jpg --skip-blockchain
```

### Custom Threshold

```powershell
python run.py --image examples/lena.jpg --threshold 0.80
```

### Verify Evidence

```powershell
python verify.py --evidence evidence_*.json
```

---

## ✅ Verification

FaceTrace has **two verification layers**:

### Layer 1: Local Integrity

- Recomputes SHA-256 from evidence JSON
- Compares with stored hash
- Detects local tampering

### Layer 2: Blockchain Verification

- Connects to blockchain
- Queries stored hash
- Compares with local hash
- Reports VERIFIED or TAMPERED

---

## ⚠️ Known Limitations

### Reverse Image Search
- Requires valid SerpAPI key
- May be rate-limited
- Private posts inaccessible
- Some platforms restrict automated access

### Face Recognition
- Affected by lighting, pose, occlusion, resolution
- Compression reduces accuracy
- **A similarity score is NOT legal proof of identity**

### Blockchain
- Provides integrity, not truth
- Hash of false info = hash of false info on-chain
- Network connectivity required

---

## 📁 Project Structure

```
FaceTrace/
├── src/
│   ├── face.py              # InsightFace / ArcFace
│   ├── reverse_search.py    # SerpAPI integration
│   ├── verifier.py          # Face similarity
│   ├── evidence.py          # JSON + SHA-256
│   └── blockchain.py         # Web3.py (dual-mode)
├── blockchain/
│   ├── contracts/
│   │   └── VerificationRegistry.sol
│   ├── scripts/
│   │   └── deploy.js
│   ├── hardhat.config.js
│   └── README.md
├── contracts/               # Original Solidity
├── tests/
├── examples/
├── run.py                   # Main CLI
├── verify.py                # Verification CLI
├── demo_test.py             # Offline test
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🎬 Demo Instructions

### Record a Demo

1. Show directory structure
2. Start Hardhat node: `cd blockchain && npx hardhat node`
3. Deploy: `npx hardhat run scripts/deploy.js --network localhost`
4. Copy contract address to `.env`
5. Run pipeline: `python run.py --image examples/lena.jpg`
6. Show discovered URL (proof of genuine search)
7. Show blockchain transaction
8. Verify: `python verify.py --evidence evidence_*.json`

### Offline Demo (No API Keys)

```powershell
python demo_test.py examples/lena.jpg
```

This tests face detection, embedding, evidence, and hashing — but NOT genuine reverse search.

---

**⚠️ Disclaimer**: This tool is for educational and research purposes. Always respect privacy, obtain consent before verifying faces, and comply with applicable laws.
