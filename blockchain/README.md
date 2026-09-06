# FaceTrace — Local Hardhat Blockchain

This directory contains the local Hardhat blockchain setup for FaceTrace.

## Why Hardhat Local?

- **No MetaMask required**
- **No real wallet private key needed** (uses Hardhat's prefunded dev accounts)
- **No POL/MATIC required** (free test ETH)
- **Real EVM transactions** with full consensus
- **Instant block mining**
- **Works offline** (no internet required for blockchain)

## Quick Start

### 1. Install Hardhat

```powershell
cd blockchain
npm install
```

### 2. Start the Local Node

In one terminal, run:

```powershell
npx hardhat node
```

You will see output like:

```
Started HTTP and WebSocket JSON-RPC server at http://127.0.0.1:8545/

Accounts
========
Account #0: 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 (10000 ETH)
Private Key: 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

Account #1: 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 (10000 ETH)
...
```

Keep this terminal running.

### 3. Deploy the Contract

In a second terminal, run:

```powershell
cd blockchain
npx hardhat run scripts/deploy.js --network localhost
```

You will get output like:

```
Contract address: 0x5FbDB2315678afecb367f032d93F642f64180aa3
```

### 4. Configure `.env`

Add to your project's root `.env`:

```env
BLOCKCHAIN_MODE=hardhat
RPC_URL=http://127.0.0.1:8545
HARDHAT_PRIVATE_KEY=0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80
CONTRACT_ADDRESS=0x5FbDB2315678afecb367f032d93F642f64180aa3
```

### 5. Run FaceTrace

```powershell
# From project root
python run.py --image examples/lena.jpg
```

The pipeline will:
1. Detect face
2. Generate embedding
3. Call SerpAPI for reverse-image search
4. Verify candidate
5. Generate evidence + SHA-256
6. **Send real transaction to local Hardhat blockchain**
7. Store hash in `VerificationRegistry`
8. Read hash back
9. Report VERIFIED

## Reset the Chain

To reset and redeploy:

```powershell
# Stop the hardhat node (Ctrl+C)
# Restart it
npx hardhat node
# Redeploy
npx hardhat run scripts/deploy.js --network localhost
# Update CONTRACT_ADDRESS in .env
```

## Hardhat Prefunded Account

| Field | Value |
|-------|-------|
| Address | `0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266` |
| Private Key | `0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80` |
| Balance | 10000 ETH (test) |

⚠️ **Never use this private key on mainnet or any real network.**

## Architecture

```
Hardhat Node (localhost:8545)
  ↓
VerificationRegistry contract
  ↓
recordVerification(bytes32 evidenceHash) → uint256 recordId
  ↓
getVerification(uint256 recordId) → (bytes32, uint256, address)
  ↓
verifyHash(bytes32 evidenceHash) → (bool, uint256)
```

## Files

| File | Purpose |
|------|---------|
| `contracts/VerificationRegistry.sol` | Smart contract |
| `scripts/deploy.js` | Deployment script |
| `hardhat.config.js` | Hardhat configuration |
| `package.json` | Node.js dependencies |
| `deployment-info.json` | Created after deployment |
