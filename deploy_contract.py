#!/usr/bin/env python3
"""
FaceTrace - Contract Deployment Helper

Deploys the VerificationRegistry contract to Polygon Amoy testnet.
Run this once to deploy your contract, then save the address to .env

Usage:
    python deploy_contract.py
"""

import os
import sys
import json
import logging

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


# Contract ABI and Bytecode (compiled from VerificationRegistry.sol)
# This is generated after compilation. For a quick start, we use a minimal ABI.
CONTRACT_ABI = [
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "recordVerification",
        "outputs": [{"internalType": "uint256", "name": "recordId", "type": "uint256"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "uint256", "name": "recordId", "type": "uint256"}],
        "name": "getVerification",
        "outputs": [
            {"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"},
            {"internalType": "uint256", "name": "timestamp", "type": "uint256"},
            {"internalType": "address", "name": "submitter", "type": "address"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"internalType": "bytes32", "name": "evidenceHash", "type": "bytes32"}],
        "name": "verifyHash",
        "outputs": [
            {"internalType": "bool", "name": "exists", "type": "bool"},
            {"internalType": "uint256", "name": "recordId", "type": "uint256"}
        ],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "totalRecords",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]


def check_config():
    """Check that all required environment variables are set"""
    rpc_url = os.getenv("RPC_URL")
    private_key = os.getenv("PRIVATE_KEY")

    if not rpc_url:
        print("✗ RPC_URL not set in .env")
        return False

    if not private_key or "0x0000000000000000000000000000000000000000000000000000000000000000" in private_key:
        print("✗ PRIVATE_KEY not set in .env (or still placeholder)")
        print("  Add your real wallet private key to .env")
        return False

    return True


def main():
    print()
    print("=" * 50)
    print("  FACETRACE - Contract Deployment")
    print("=" * 50)
    print()

    if not check_config():
        print()
        print("Please configure .env with valid RPC_URL and PRIVATE_KEY first.")
        print()
        print("Recommended steps:")
        print("1. Install MetaMask: https://metamask.io")
        print("2. Add Polygon Amoy testnet to MetaMask")
        print("3. Get test MATIC: https://faucet.polygon.technology/")
        print("4. Export your private key from MetaMask")
        print("5. Add to .env: PRIVATE_KEY=0x...")
        print()
        sys.exit(1)

    print("This helper prepares your contract deployment.")
    print()
    print("=" * 50)
    print("OPTION A: Deploy via Remix (Easiest)")
    print("=" * 50)
    print()
    print("1. Open https://remix.ethereum.org")
    print("2. Create file: VerificationRegistry.sol")
    print("3. Copy contents from: contracts/VerificationRegistry.sol")
    print("4. Compile with Solidity 0.8.19+")
    print("5. Switch to 'Deploy & Run' tab")
    print("6. Environment: 'Injected Provider - MetaMask'")
    print("7. Make sure MetaMask is on Polygon Amoy")
    print("8. Click 'Deploy'")
    print("9. Copy the deployed contract address")
    print("10. Add to .env: CONTRACT_ADDRESS=0x...")
    print()

    print("=" * 50)
    print("OPTION B: Use this Python helper")
    print("=" * 50)
    print()
    print("To deploy programmatically, you need the contract bytecode.")
    print("Compile contracts/VerificationRegistry.sol first:")
    print()
    print("  solc --bin --abi contracts/VerificationRegistry.sol --optimize -o build/")
    print()
    print("Then run the deployment script with the bytecode.")
    print()
    print("=" * 50)
    print("VERIFICATION (after deployment)")
    print("=" * 50)
    print()
    print("After setting CONTRACT_ADDRESS in .env, test the connection:")
    print()
    print("  python verify.py --evidence examples/demo_evidence.json")
    print()


if __name__ == "__main__":
    main()
