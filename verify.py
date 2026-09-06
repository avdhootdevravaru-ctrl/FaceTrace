#!/usr/bin/env python3
"""
FaceTrace - Verification CLI

Verify an evidence record against the blockchain.

Usage:
    python verify.py --evidence evidence.json
    python verify.py --evidence evidence.json --hash 8f31a7c9...e921
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.blockchain import create_blockchain_client
from src.evidence import create_evidence_generator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ASCII Banner
BANNER = """
========================================
     FACETRACE VERIFICATION CHECK
========================================
"""


def print_section(title: str):
    """Print a section header"""
    print()
    print(f"=== {title} ===")


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="Verify evidence record against the blockchain",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify.py --evidence evidence.json
  python verify.py --evidence evidence.json --hash 8f31a7c9e921...
  python verify.py --evidence evidence.json --record-id 42
        """
    )

    parser.add_argument(
        '--evidence', '-e',
        type=str,
        required=True,
        help='Path to evidence JSON file'
    )

    parser.add_argument(
        '--hash', '-H',
        type=str,
        default=None,
        help='Evidence hash to verify (overrides file hash)'
    )

    parser.add_argument(
        '--record-id', '-r',
        type=int,
        default=None,
        help='Blockchain record ID to verify against'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    return parser.parse_args()


def compute_evidence_hash(evidence_path: str) -> str:
    """
    Compute the SHA-256 hash of an evidence record.

    Uses the same canonical EvidenceGenerator method as run.py to ensure
    both tools produce identical hashes for the same data.

    Args:
        evidence_path: Path to evidence JSON file

    Returns:
        SHA-256 hash as hex string
    """
    eg = create_evidence_generator()
    with open(evidence_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return eg.compute_evidence_hash_from_dict(data)


def verify_local_integrity(evidence_path: str) -> tuple:
    """
    Verify that the evidence file hasn't been tampered with.

    Args:
        evidence_path: Path to evidence JSON file

    Returns:
        Tuple of (is_valid, stored_hash, computed_hash)
    """
    with open(evidence_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stored_hash = data.get("evidence_hash", "")

    if not stored_hash:
        return (False, "", None, "No hash in evidence file")

    computed_hash = compute_evidence_hash(evidence_path)

    is_valid = computed_hash == stored_hash

    if is_valid:
        return (True, stored_hash, computed_hash, None)
    else:
        return (False, stored_hash, computed_hash, "Hash mismatch - file may have been tampered with")


def verify_blockchain(evidence_hash: str, record_id: int = None) -> dict:
    """
    Verify evidence hash against the blockchain.

    Args:
        evidence_hash: SHA-256 hash to verify
        record_id: Optional record ID to check

    Returns:
        Dictionary with verification results
    """
    results = {
        "hash": evidence_hash,
        "connected": False,
        "hash_exists": False,
        "record_id": None,
        "timestamp": None,
        "submitter": None,
        "verified": False,
        "network": None
    }

    try:
        blockchain = create_blockchain_client()

        if not blockchain.connect():
            results["error"] = "Failed to connect to blockchain. Check .env configuration."
            return results

        results["connected"] = True
        if blockchain.mode == "hardhat":
            results["network"] = f"Hardhat Local (chain ID: {blockchain.w3.eth.chain_id})"
        else:
            results["network"] = f"Polygon Amoy (chain ID: {blockchain.w3.eth.chain_id})"

        # Check if hash exists
        exists, found_id = blockchain.verify_hash(evidence_hash)

        if not exists:
            results["hash_exists"] = False
            results["error"] = "Hash not found on blockchain"
            return results

        results["hash_exists"] = True
        results["record_id"] = found_id

        # Get verification record
        record = blockchain.get_verification(found_id)

        if record:
            results["timestamp"] = record.get("datetime")
            results["submitter"] = record.get("submitter")
            results["on_chain_hash"] = record.get("evidence_hash")
            results["verified"] = True

    except Exception as e:
        results["error"] = str(e)
        logger.exception("Blockchain verification error")

    return results


def display_evidence_summary(evidence_path: str):
    """Display evidence summary from file"""
    print_section("Evidence Summary")

    with open(evidence_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Key fields
    print(f"  Input image hash:    {data.get('input_image_hash', 'N/A')[:16]}...")
    print(f"  Matched URL:         {data.get('matched_url', 'N/A')}")
    print(f"  Platform:           {data.get('platform', 'N/A')}")
    print(f"  Face similarity:    {data.get('face_similarity', 'N/A')}")
    print(f"  Threshold:          {data.get('verification_threshold', 'N/A')}")
    print(f"  Status:             {data.get('verification_status', 'N/A')}")
    print(f"  Timestamp:          {data.get('timestamp', 'N/A')}")

    if data.get("blockchain_tx"):
        print(f"  Blockchain TX:      {data.get('blockchain_tx')[:16]}...")

    print(f"  Evidence hash:      {data.get('evidence_hash', 'N/A')[:16]}...")


def main():
    """Main entry point"""
    args = parse_arguments()

    # Set verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    print(BANNER)

    # Check file exists
    if not os.path.exists(args.evidence):
        print(f"ERROR: Evidence file not found: {args.evidence}")
        sys.exit(1)

    # Display evidence summary
    display_evidence_summary(args.evidence)

    # ===== LOCAL INTEGRITY CHECK =====
    print_section("Local Integrity Check")

    is_valid, stored_hash, computed_hash, error = verify_local_integrity(args.evidence)

    print(f"  Stored hash:        {stored_hash}")
    print(f"  Computed hash:      {computed_hash}")

    if is_valid:
        print()
        print("  Local integrity:    ✓ VALID")
        print("  The evidence file has not been tampered with.")
    else:
        print()
        print("  Local integrity:    ✗ INVALID")
        print(f"  Error: {error}")
        print()
        print("  STATUS: TAMPERED")
        sys.exit(1)

    # ===== BLOCKCHAIN VERIFICATION =====
    print_section("Blockchain Verification")

    # Determine which hash to verify
    if args.hash:
        evidence_hash = args.hash
    else:
        evidence_hash = stored_hash

    print(f"  Verifying hash:     {evidence_hash}")

    if args.record_id:
        print(f"  Checking record ID: {args.record_id}")

    # Perform blockchain verification
    bc_results = verify_blockchain(evidence_hash, args.record_id)

    if not bc_results.get("connected"):
        print()
        print("  Blockchain:         ✗ NOT CONNECTED")
        print(f"  Error: {bc_results.get('error', 'Unknown error')}")
        print()
        print("  STATUS: UNVERIFIED (BLOCKCHAIN UNAVAILABLE)")
        print()
        print("  To enable blockchain verification:")
        print("  1. Start Hardhat node: cd blockchain && npx hardhat node")
        print("  2. Deploy VerificationRegistry: cd blockchain && npx hardhat run scripts/deploy.js")
        print("  3. Ensure CONTRACT_ADDRESS is set in .env")
        # Still show local integrity result
        sys.exit(0 if is_valid else 1)

    print(f"  Network:            ✓ {bc_results.get('network', 'Connected')}")

    if bc_results.get("hash_exists"):
        print(f"  Hash exists:        ✓ YES")
        print(f"  Record ID:          {bc_results.get('record_id')}")
        print(f"  Timestamp:          {bc_results.get('timestamp')}")
        print(f"  Submitter:          {bc_results.get('submitter')}")

        # Compare hashes
        on_chain_hash = bc_results.get('on_chain_hash', '')
        print()
        print(f"  On-chain hash:      {on_chain_hash[:32]}...")
        print(f"  Local hash:         {evidence_hash[:32]}...")

        if on_chain_hash.lower() == evidence_hash.lower():
            print(f"  Hash match:         ✓ YES")
            print()
            print("  STATUS: ✓ VERIFIED")
            print()
            print("  The evidence hash has been confirmed on the blockchain.")
            print("  This provides tamper-evident proof that this verification")
            print("  record existed at the stated timestamp.")
        else:
            print(f"  Hash match:         ✗ NO")
            print()
            print("  STATUS: ✗ HASH MISMATCH")
            print()
            print("  The on-chain hash doesn't match the local hash.")

    else:
        print(f"  Hash exists:        ✗ NO")
        print()
        print("  STATUS: ✗ NOT FOUND ON BLOCKCHAIN")
        print()
        print("  The evidence hash was not found in the blockchain registry.")
        print("  This could mean:")
        print("  - The blockchain transaction was not submitted")
        print("  - The contract address is incorrect")
        print("  - The blockchain has been reset")

    # ===== FINAL STATUS =====
    print()
    print("=" * 42)

    if is_valid and bc_results.get("verified"):
        print("       ✓ FULLY VERIFIED")
        print("=" * 42)
        sys.exit(0)
    elif is_valid:
        print("       ✓ LOCALLY VALID")
        print("=" * 42)
        sys.exit(0)
    else:
        print("       ✗ INTEGRITY FAILED")
        print("=" * 42)
        sys.exit(1)


if __name__ == "__main__":
    main()
