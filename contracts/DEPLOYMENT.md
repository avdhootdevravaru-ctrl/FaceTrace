# Smart Contract Deployment Guide

## VerificationRegistry.sol

This document describes how to deploy and interact with the `VerificationRegistry` smart contract.

## Deployment Options

### Option 1: Remix IDE (Recommended for Beginners)

1. **Open Remix IDE**
   - Go to https://remix.ethereum.org/

2. **Create Contract File**
   - Click "Contracts" folder
   - Click "+" to create new file
   - Name it `VerificationRegistry.sol`

3. **Paste Contract Code**
   - Copy contents from `contracts/VerificationRegistry.sol`
   - Paste into the Remix editor

4. **Compile**
   - Go to "Solidity Compiler" tab (left sidebar)
   - Select compiler version 0.8.19+
   - Click "Compile VerificationRegistry.sol"

5. **Deploy**
   - Go to "Deploy & Run Transactions" tab
   - Select "Injected Provider - MetaMask" as Environment
   - Make sure MetaMask is connected to Polygon Amoy Testnet
   - Click "Deploy" button
   - Confirm in MetaMask

6. **Copy Contract Address**
   - After deployment, copy the contract address from Remix
   - Add it to your `.env` file as `CONTRACT_ADDRESS`

### Option 2: Hardhat

1. **Setup Hardhat**
   ```bash
   npm init -y
   npm install --save-dev hardhat @openzeppelin/contracts
   npx hardhat init
   ```

2. **Create Deployment Script**
   ```javascript
   // scripts/deploy.js
   async function main() {
     const VerificationRegistry = await ethers.getContractFactory("VerificationRegistry");
     const registry = await VerificationRegistry.deploy();
     await registry.deployed();
     console.log("VerificationRegistry deployed to:", registry.address);
   }

   main().catch((error) => {
     console.error(error);
     process.exitCode = 1;
   });
   ```

3. **Configure Network**
   ```javascript
   // hardhat.config.js
   module.exports = {
     solidity: "0.8.19",
     networks: {
       polygonAmoy: {
         url: "https://rpc-amoy.polygon.technology",
         accounts: [process.env.PRIVATE_KEY]
       }
     }
   };
   ```

4. **Deploy**
   ```bash
   PRIVATE_KEY=your_key npx hardhat run scripts/deploy.js --network polygonAmoy
   ```

## Contract Interface

### Functions

#### `recordVerification(bytes32 evidenceHash) → uint256`
Records a new evidence hash on the blockchain.

```solidity
contract.recordVerification(evidenceHash);
```

#### `getVerification(uint256 recordId) → (bytes32, uint256, address)`
Retrieves a verification record by ID.

```solidity
(evidenceHash, timestamp, submitter) = contract.getVerification(recordId);
```

#### `verifyHash(bytes32 evidenceHash) → (bool, uint256)`
Checks if an evidence hash exists and returns its record ID.

```solidity
(exists, recordId) = contract.verifyHash(evidenceHash);
```

#### `totalRecords() → uint256`
Returns the total number of verification records.

```solidity
count = contract.totalRecords();
```

### Events

#### `VerificationRecorded`
Emitted when a new verification is recorded.

```solidity
event VerificationRecorded(
    uint256 indexed recordId,
    bytes32 indexed evidenceHash,
    uint256 timestamp,
    address indexed submitter
);
```

#### `VerificationAccessed`
Emitted when a verification is accessed.

```solidity
event VerificationAccessed(
    uint256 indexed recordId,
    bytes32 indexed evidenceHash,
    uint256 timestamp
);
```

## Verification

After deployment, verify the contract on Polygonscan:

1. Go to https://amoy.polygonscan.com/
2. Search for your contract address
3. Click "Contract" tab
4. Select "Verify and Publish"
5. Fill in:
   - Contract name: `VerificationRegistry`
   - Compiler version: `0.8.19`
   - License: `MIT License (MIT)`
6. Paste the contract source code
7. Click "Verify and Publish"

## Security Considerations

1. **Immutable Contract**: This contract cannot be modified after deployment
2. **No Admin Keys**: There is no owner or admin that can modify records
3. **Permissionless**: Anyone can call `recordVerification()`
4. **Data Storage**: Only evidence hashes are stored, no sensitive data

## Gas Costs (Polygon Amoy)

| Operation | Approximate Gas |
|-----------|-----------------|
| `recordVerification` | ~45,000 |
| `getVerification` | ~0 (view call) |
| `verifyHash` | ~0 (view call) |

At current MATIC prices, each record costs less than $0.01.
