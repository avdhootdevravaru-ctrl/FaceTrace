"""
Blockchain Module - Dual Mode Support

Supports two blockchain backends:
1. Hardhat Local (BLOCKCHAIN_MODE=hardhat)
   - Uses localhost:8545
   - Chain ID: 31337
   - Uses Hardhat prefunded development account
   - No MetaMask, POL, or real wallet required

2. Polygon Amoy (BLOCKCHAIN_MODE=polygon)
   - Uses public RPC endpoints
   - Chain ID: 80002
   - Requires MetaMask wallet with test MATIC

Both modes expose the same interface:
- connect() → connect to blockchain
- submit_evidence(hash) → store hash, return tx hash
- verify_hash(hash) → check if hash exists
- get_verification(id) → retrieve record

IMPORTANT: Only evidence hashes are stored on-chain. Sensitive information
like photographs, face embeddings, and private content are never stored
on the blockchain.
"""

import os
import json
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TransactionResult:
    """Result of a blockchain transaction"""
    success: bool
    transaction_hash: Optional[str]
    block_number: Optional[int]
    record_id: Optional[int]
    gas_used: Optional[int]
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "transaction_hash": self.transaction_hash,
            "block_number": self.block_number,
            "record_id": self.record_id,
            "gas_used": self.gas_used,
            "error": self.error
        }


class BlockchainClient:
    """
    Client for interacting with blockchain (Hardhat or Polygon).

    The backend is determined by BLOCKCHAIN_MODE environment variable:
    - "hardhat": Local Hardhat node (localhost:8545, chain ID 31337)
    - "polygon": Polygon Amoy testnet (chain ID 80002)

    Attributes:
        mode: Current blockchain mode ("hardhat" or "polygon")
        rpc_url: RPC endpoint URL
        private_key: Wallet private key
        contract_address: Deployed contract address
        chain_id: Expected chain ID for the configured network
    """

    # Default ABI for VerificationRegistry contract
    _default_abi = [
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

    def __init__(
        self,
        rpc_url: Optional[str] = None,
        private_key: Optional[str] = None,
        contract_address: Optional[str] = None,
        contract_abi: Optional[str] = None,
        blockchain_mode: Optional[str] = None
    ):
        """
        Initialize the blockchain client.

        Args:
            rpc_url: Blockchain RPC URL
            private_key: Wallet private key (for sending transactions)
            contract_address: Deployed smart contract address
            contract_abi: Smart contract ABI
            blockchain_mode: "hardhat" or "polygon" (overrides env var)
        """
        # Determine blockchain mode
        self.mode = blockchain_mode or os.getenv("BLOCKCHAIN_MODE", "hardhat").lower()

        # Mode-specific defaults
        if self.mode == "hardhat":
            self.chain_id = 31337
            self.rpc_url = rpc_url or os.getenv("RPC_URL", "http://127.0.0.1:8545")
            # Hardhat dev account - only used when BLOCKCHAIN_MODE=hardhat
            self.private_key = private_key or os.getenv("HARDHAT_PRIVATE_KEY") or os.getenv("PRIVATE_KEY")
        elif self.mode == "polygon":
            self.chain_id = 80002
            self.rpc_url = rpc_url or os.getenv("RPC_URL", "https://rpc-amoy.polygon.technology")
            self.private_key = private_key or os.getenv("PRIVATE_KEY")
        else:
            raise ValueError(f"Unknown BLOCKCHAIN_MODE: {self.mode}. Use 'hardhat' or 'polygon'.")

        self.contract_address = contract_address or os.getenv("CONTRACT_ADDRESS")
        self._abi = contract_abi or json.dumps(self._default_abi)

        # Runtime state
        self.w3 = None
        self.contract = None
        self.account = None

    def _get_diagnostic_info(self) -> Dict[str, Any]:
        """Get diagnostic information about configuration"""
        return {
            "mode": self.mode,
            "chain_id_expected": self.chain_id,
            "rpc_url": self.rpc_url,
            "contract_configured": bool(self.contract_address and self.contract_address != "0x" + "0" * 40),
            "private_key_configured": bool(self.private_key and len(self.private_key) >= 32),
            "private_key_preview": self.private_key[:10] + "..." if self.private_key and len(self.private_key) > 10 else None
        }

    def connect(self) -> bool:
        """
        Connect to the blockchain.

        Returns:
            True if connection successful
        """
        try:
            from web3 import Web3

            # Check configuration
            if not self.rpc_url:
                print(f"  [*] RPC_URL not configured for {self.mode} mode")
                return False

            # Connect to blockchain
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url, request_kwargs={'timeout': 30}))

            # Check connection
            if not self.w3.is_connected():
                print(f"  [*] Cannot connect to RPC: {self.rpc_url}")
                print(f"      Check if blockchain node is running")
                if self.mode == "hardhat":
                    print(f"      Run: cd blockchain && npx hardhat node")
                return False

            # Get actual chain ID
            actual_chain_id = self.w3.eth.chain_id
            logger.info(f"Connected to chain ID: {actual_chain_id}")

            # Verify chain ID matches expected
            if actual_chain_id != self.chain_id:
                print(f"  [*] Wrong network: chain ID {actual_chain_id} (expected {self.chain_id})")
                print(f"      For {self.mode} mode, chain ID should be {self.chain_id}")
                if self.mode == "hardhat":
                    print(f"      Make sure you're running local Hardhat node")

            # Setup contract
            if self.contract_address and self.contract_address != "0x" + "0" * 40:
                try:
                    self.contract = self.w3.eth.contract(
                        address=self.w3.to_checksum_address(self.contract_address),
                        abi=json.loads(self._abi)
                    )
                    print(f"  [*] Contract loaded: {self.contract_address}")
                except Exception as e:
                    print(f"  [*] Contract error: {e}")
                    return False
            else:
                print(f"  [*] CONTRACT_ADDRESS not set")
                print(f"      Deploy VerificationRegistry and set CONTRACT_ADDRESS in .env")
                return False

            # Setup account
            if self.private_key and len(self.private_key) >= 32:
                try:
                    self.account = self.w3.eth.account.from_key(self.private_key)
                    print(f"  [*] Account: {self.account.address}")
                    balance = self.w3.eth.get_balance(self.account.address)
                    print(f"  [*] Balance: {self.w3.from_wei(balance, 'ether'):.4f} ETH")
                except Exception as e:
                    print(f"  [*] Account error: {e}")
                    return False
            else:
                print(f"  [*] Private key not configured")
                print(f"      Set HARDHAT_PRIVATE_KEY (hardhat mode) or PRIVATE_KEY (polygon mode)")
                return False

            print(f"  [+] Connected to {self.mode} blockchain")
            return True

        except ImportError:
            print("  [*] web3 library not installed. Run: pip install web3")
            return False
        except Exception as e:
            print(f"  [*] Connection error: {type(e).__name__}: {e}")
            return False

    def is_connected(self) -> bool:
        """Check if connected to blockchain"""
        if self.w3 is None:
            return False
        try:
            return self.w3.is_connected() and self.contract is not None
        except:
            return False

    def submit_evidence(self, evidence_hash: str) -> TransactionResult:
        """
        Submit an evidence hash to the blockchain.

        Args:
            evidence_hash: SHA-256 hash of the evidence record

        Returns:
            TransactionResult with transaction details
        """
        if not self.is_connected():
            success = self.connect()
            if not success:
                return TransactionResult(
                    success=False,
                    transaction_hash=None,
                    block_number=None,
                    record_id=None,
                    gas_used=None,
                    error=f"Cannot connect to {self.mode} blockchain. Check configuration."
                )

        try:
            # Convert hash to bytes32
            evidence_bytes = bytes.fromhex(evidence_hash.replace('0x', ''))

            # Build transaction
            nonce = self.w3.eth.get_transaction_count(self.account.address)
            chain_id = self.w3.eth.chain_id

            txn = self.contract.functions.recordVerification(evidence_bytes).build_transaction({
                'from': self.account.address,
                'nonce': nonce,
                'chainId': chain_id,
                'gas': 500000,
                'gasPrice': self.w3.eth.gas_price
            })

            # Sign and send transaction
            signed_txn = self.w3.eth.account.sign_transaction(txn, self.private_key)
            tx_hash = self.w3.eth.send_raw_transaction(signed_txn.raw_transaction)
            tx_hash_hex = tx_hash.hex()

            logger.info(f"Transaction sent: {tx_hash_hex}")

            # Wait for receipt
            receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)

            # Extract record ID from logs
            record_id = None
            if receipt.logs:
                try:
                    log_data = receipt.logs[0]['data']
                    record_id = int(log_data.hex(), 16)
                except Exception:
                    # Try to estimate record ID from total records
                    try:
                        record_id = self.contract.functions.totalRecords().call()
                    except:
                        pass

            logger.info(f"Transaction confirmed in block {receipt.blockNumber}")

            return TransactionResult(
                success=True,
                transaction_hash=tx_hash_hex,
                block_number=receipt.blockNumber,
                record_id=record_id,
                gas_used=receipt.gasUsed
            )

        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return TransactionResult(
                success=False,
                transaction_hash=None,
                block_number=None,
                record_id=None,
                gas_used=None,
                error=str(e)
            )

    def get_verification(self, record_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a verification record from the blockchain.

        Args:
            record_id: ID of the record to retrieve

        Returns:
            Dictionary with record data or None if not found
        """
        if not self.is_connected():
            success = self.connect()
            if not success:
                return None

        if self.contract is None:
            logger.error("Contract not configured")
            return None

        try:
            evidence_hash, timestamp, submitter = self.contract.functions.getVerification(record_id).call()

            return {
                "record_id": record_id,
                "evidence_hash": evidence_hash.hex() if isinstance(evidence_hash, (bytes, bytearray)) else evidence_hash,
                "timestamp": timestamp,
                "submitter": submitter,
                "datetime": datetime.fromtimestamp(timestamp).isoformat() if timestamp else None
            }
        except Exception as e:
            logger.error(f"Failed to get verification: {e}")
            return None

    def verify_hash(self, evidence_hash: str) -> Tuple[bool, Optional[int]]:
        """
        Verify that an evidence hash exists on the blockchain.

        Args:
            evidence_hash: SHA-256 hash to verify

        Returns:
            Tuple of (exists, record_id)
        """
        if not self.is_connected():
            success = self.connect()
            if not success:
                return (False, None)

        if self.contract is None:
            logger.error("Contract not configured")
            return (False, None)

        try:
            evidence_bytes = bytes.fromhex(evidence_hash.replace('0x', ''))
            exists, record_id = self.contract.functions.verifyHash(evidence_bytes).call()
            return (exists, record_id if exists else None)
        except Exception as e:
            logger.error(f"Failed to verify hash: {e}")
            return (False, None)

    def get_total_records(self) -> int:
        """Get total number of verification records"""
        if not self.is_connected():
            success = self.connect()
            if not success:
                return 0

        if self.contract is None:
            return 0

        try:
            return self.contract.functions.totalRecords().call()
        except Exception as e:
            logger.error(f"Failed to get total records: {e}")
            return 0

    def get_block_info(self) -> Optional[Dict[str, Any]]:
        """Get current block information"""
        if not self.is_connected():
            return None

        try:
            block = self.w3.eth.get_block('latest')
            return {
                "number": block.number,
                "hash": block.hash.hex(),
                "timestamp": block.timestamp,
                "datetime": datetime.fromtimestamp(block.timestamp).isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get block info: {e}")
            return None


def create_blockchain_client(blockchain_mode: Optional[str] = None) -> BlockchainClient:
    """
    Factory function to create a BlockchainClient instance.

    Args:
        blockchain_mode: Optional mode override ("hardhat" or "polygon")

    Returns:
        BlockchainClient configured based on BLOCKCHAIN_MODE env var
    """
    return BlockchainClient(blockchain_mode=blockchain_mode)
