#!/usr/bin/env python3
"""
FaceTrace - Main CLI Entry Point

Run the complete face verification pipeline:
1. Detect face in input image
2. Generate face embedding
3. Perform reverse image search
4. Verify candidates with face similarity
5. Generate evidence record
6. Commit evidence hash to blockchain

Usage:
    python run.py --image ./input.jpg
    python run.py --image ./input.jpg --threshold 0.80
"""

import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.face import get_face_encoder
from src.reverse_search import create_searcher, filter_social_media_results
from src.verifier import create_verifier
from src.evidence import create_evidence_generator
from src.blockchain import create_blockchain_client

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('facetrace.log'),
        logging.StreamHandler()
    ]
)

# Suppress verbose library logging
logging.getLogger('insightface').setLevel(logging.ERROR)
logging.getLogger('PIL').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ASCII Banner
BANNER = """
========================================
       FACETRACE VERIFICATION
========================================
"""


def print_step(step: int, total: int, message: str, status: str = "OK"):
    """Print a step with status"""
    symbols = {"OK": "✓", "FAIL": "✗", "...": "..."}
    symbol = symbols.get(status, status)
    print(f"[{step}/{total}] {message:.<30} {symbol}")


def print_section(title: str):
    """Print a section header"""
    print()
    print(f"=== {title} ===")
    print()


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="FaceTrace - Face Identity & Blockchain Verification Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --image examples/person.jpg
  python run.py --image person.jpg --threshold 0.80
  python run.py --image person.jpg --output my_evidence.json
        """
    )

    parser.add_argument(
        '--image', '-i',
        type=str,
        required=True,
        help='Path to input image file (JPG, JPEG, PNG, WEBP)'
    )

    parser.add_argument(
        '--threshold', '-t',
        type=float,
        default=float(os.getenv('SIMILARITY_THRESHOLD', '0.75')),
        help='Face similarity threshold (0.0-1.0, default: 0.75)'
    )

    parser.add_argument(
        '--output', '-o',
        type=str,
        default=None,
        help='Output path for evidence JSON file'
    )

    parser.add_argument(
        '--max-candidates', '-m',
        type=int,
        default=int(os.getenv('MAX_CANDIDATES', '5')),
        help='Maximum number of candidates to verify (default: 5)'
    )

    parser.add_argument(
        '--skip-blockchain',
        action='store_true',
        help='Skip blockchain transaction (local evidence only)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    return parser.parse_args()


def validate_image(image_path: str) -> bool:
    """Validate that the image file exists and is supported"""
    if not os.path.exists(image_path):
        print(f"\nERROR: Image not found: {image_path}")
        return False

    valid_extensions = ['.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(image_path)[1].lower()

    if ext not in valid_extensions:
        print(f"\nERROR: Unsupported image format: {ext}")
        print(f"Supported formats: {', '.join(valid_extensions)}")
        return False

    return True


def run_pipeline(
    image_path: str,
    threshold: float = 0.75,
    output_path: str = None,
    max_candidates: int = 5,
    skip_blockchain: bool = False
) -> dict:
    """
    Run the complete FaceTrace verification pipeline.

    Args:
        image_path: Path to input image
        threshold: Face similarity threshold
        output_path: Path for evidence output
        max_candidates: Maximum candidates to verify
        skip_blockchain: Skip blockchain transaction

    Returns:
        Dictionary with pipeline results
    """
    print(BANNER)

    # Track pipeline state
    results = {
        "success": False,
        "image": image_path,
        "threshold": threshold,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    # ============ STEP 1: Load Image ============
    print_step(1, 7, "Loading image", "...")
    time.sleep(0.3)
    if not validate_image(image_path):
        return results
    print_step(1, 7, "Loading image", "OK")

    # ============ STEP 2: Detect Face ============
    print_step(2, 7, "Detecting face", "...")
    try:
        face_encoder = get_face_encoder()
        face_result = face_encoder.detect_face(image_path)

        results["face_detected"] = True
        results["bounding_box"] = list(face_result.bbox)
        results["face_confidence"] = face_result.confidence

        print_step(2, 7, "Detecting face", "OK")
        logger.info(f"Face detected at {face_result.bbox} (confidence: {face_result.confidence:.4f})")
    except ValueError as e:
        print_step(2, 7, "Detecting face", "FAIL")
        print(f"\nERROR: {str(e)}")
        return results
    except Exception as e:
        print_step(2, 7, "Detecting face", "FAIL")
        print(f"\nERROR: Face detection failed: {e}")
        logger.exception("Face detection error")
        return results

    # ============ STEP 3: Generate Embedding ============
    print_step(3, 7, "Generating embedding", "...")
    time.sleep(0.3)
    input_embedding = face_result.embedding
    results["embedding_generated"] = True
    results["embedding_dim"] = len(input_embedding)
    print_step(3, 7, "Generating embedding", "OK")
    logger.info(f"Generated embedding of dimension {len(input_embedding)}")

    # ============ STEP 4: Reverse Image Search ============
    print_step(4, 7, "Reverse image search", "...")
    try:
        searcher = create_searcher()
        search_results = searcher.search(image_path)

        # Filter for social media
        social_results = filter_social_media_results(search_results)

        if not social_results:
            print_step(4, 7, "Reverse image search", "FAIL")
            print()
            print("ERROR: No matching social-media result found.")
            print()
            print("This means the reverse-image-search API executed but")
            print("returned no results that match supported social-media platforms.")
            print()
            if not searcher.providers_used:
                print("Search providers used: NONE (all failed)")
                print("Check your API key in .env")
            else:
                print(f"Search providers used: {', '.join(searcher.providers_used)}")
                print("Try a different input image or check API quota.")
            results["search_success"] = False
            return results

        # Get candidate URLs (up to max_candidates)
        candidate_urls = []
        candidate_image_urls = []
        for r in social_results[:max_candidates]:
            candidate_urls.append(r.url)
            candidate_image_urls.append(r.image_url)
            if not r.platform:
                r.platform = searcher.detect_platform(r.url)

        results["search_success"] = True
        results["candidates_found"] = len(candidate_urls)
        results["search_providers"] = searcher.providers_used
        results["search_query_timestamp"] = searcher.last_query_timestamp
        results["search_method"] = "reverse_image_search_api"

        print_step(4, 7, "Reverse image search", "OK")
        print()
        print(f"   Providers used:    {', '.join(searcher.providers_used)}")
        print(f"   Query timestamp:   {searcher.last_query_timestamp}")
        print(f"   Candidates found:  {len(candidate_urls)} social media result(s)")
        for i, (url, img_url) in enumerate(zip(candidate_urls, candidate_image_urls), 1):
            platform = searcher.detect_platform(url) or "Unknown"
            if img_url and img_url != url:
                print(f"   [{i}] {platform}: {url}")
                print(f"       Image: {img_url}")
            else:
                print(f"   [{i}] {platform}: {url}")

    except Exception as e:
        print_step(4, 7, "Reverse image search", "FAIL")
        print(f"\nERROR: Reverse image search failed: {e}")
        logger.exception("Reverse search error")
        results["search_success"] = False
        return results

    # ============ STEP 5: Verify Candidates ============
    print_step(5, 7, "Verifying candidates", "...")
    try:
        verifier = create_verifier(face_encoder, threshold=threshold)
        verification_result = verifier.find_best_match(
            candidate_urls,
            input_embedding,
            image_urls=candidate_image_urls
        )

        if verification_result is None:
            print_step(5, 7, "Verifying candidates", "FAIL")
            print("\nERROR: No candidates could be verified.")
            results["match_found"] = False
            return results

        if not verification_result.verified:
            print_step(5, 7, "Verifying candidates", "FAIL")
            print(f"\nERROR: No candidate met the similarity threshold of {threshold}")
            print(f"   Best similarity: {verification_result.similarity:.4f}")
            results["match_found"] = False
            results["best_similarity"] = verification_result.similarity
            return results

        results["match_found"] = True
        results["matched_url"] = verification_result.url
        results["platform"] = verification_result.platform
        results["face_similarity"] = verification_result.similarity

        print_step(5, 7, "Verifying candidates", "OK")
        print()
        print("MATCH FOUND")
        print()
        print(f"   Platform:          {verification_result.platform}")
        print(f"   URL:               {verification_result.url}")
        print(f"   Face similarity:   {verification_result.similarity:.4f}")
        print(f"   Threshold:         {threshold}")

    except Exception as e:
        print_step(5, 7, "Verifying candidates", "FAIL")
        print(f"\nERROR: Verification failed: {e}")
        logger.exception("Verification error")
        results["match_found"] = False
        return results

    # ============ STEP 6: Create Evidence ============
    print_step(6, 7, "Creating evidence", "...")
    try:
        evidence_gen = create_evidence_generator()

        evidence = evidence_gen.create_evidence(
            input_image_path=image_path,
            matched_url=verification_result.url,
            platform=verification_result.platform,
            face_similarity=verification_result.similarity,
            threshold=threshold,
            reverse_search_method="reverse_image_search_api",
            candidate_count=len(candidate_urls)
        )

        # Build the evidence dict (blockchain fields added in Step 7)
        evidence_dict = evidence.to_dict()

        # Compute initial hash (from evidence without blockchain fields — used for filename)
        initial_hash = evidence_gen.compute_evidence_hash_from_dict(evidence_dict)

        # Auto-generate filename if not provided
        if output_path is None:
            ts = time.strftime("%Y%m%d_%H%M%S", time.gmtime())
            output_path = f"evidence_{ts}_{initial_hash[:8]}.json"

        # Save evidence without blockchain fields first
        evidence_dict_with_hash = dict(evidence_dict)
        evidence_dict_with_hash['evidence_hash'] = initial_hash
        with open(output_path, 'w') as f:
            json.dump(evidence_dict_with_hash, f, indent=2)

        evidence_path = output_path
        evidence_hash = initial_hash
        results["evidence_path"] = evidence_path
        results["evidence_hash"] = evidence_hash

        print_step(6, 7, "Creating evidence", "OK")
        print()
        print(f"   Evidence SHA256:")
        print(f"   {evidence_hash}")

    except Exception as e:
        print_step(6, 7, "Creating evidence", "FAIL")
        print(f"\nERROR: Evidence creation failed: {e}")
        logger.exception("Evidence error")
        return results

    # ============ STEP 7: Blockchain Transaction ============
    # After blockchain succeeds: add tx fields to dict, compute COMPLETE hash,
    # submit that hash to the chain, then overwrite the file so stored_hash
    # and on-chain hash are identical.
    if skip_blockchain:
        print_step(7, 7, "Blockchain transaction", "SKIP")
        print()
        print("   Skipped (--skip-blockchain flag)")
        print(f"   Evidence preserved locally: {evidence_path}")
    else:
        print_step(7, 7, "Blockchain transaction", "...")
        try:
            blockchain = create_blockchain_client()

            if not blockchain.connect():
                print_step(7, 7, "Blockchain transaction", "FAIL")
                print()
                print("   Blockchain connection failed.")
                print(f"   Evidence preserved locally: {evidence_path}")
                print()
                print("   To enable blockchain:")
                print("   1. Start Hardhat node: cd blockchain && npx hardhat node")
                print("   2. Deploy VerificationRegistry: cd blockchain && npx hardhat run scripts/deploy.js")
                print("   3. CONTRACT_ADDRESS already set in .env")
                results["blockchain_success"] = False
                results["blockchain_error"] = "Connection failed"
            else:
                if blockchain.mode == "hardhat":
                    network_label = "Hardhat Local"
                else:
                    network_label = "Polygon Amoy"
                print(f"   Network:  {network_label} (chain ID: {blockchain.w3.eth.chain_id})")

                # Build the complete evidence dict first (with blockchain fields)
                with open(evidence_path, 'r') as f:
                    evidence_data = json.load(f)

                # Step 1: Submit the original hash (without blockchain fields) to get tx result
                tx_result = blockchain.submit_evidence(evidence_hash)

                if tx_result.success:
                    # Step 2: Add real blockchain values and compute COMPLETE hash
                    evidence_data['blockchain_tx'] = tx_result.transaction_hash
                    evidence_data['block_number'] = tx_result.block_number
                    evidence_data['record_id'] = tx_result.record_id
                    complete_hash = evidence_gen.compute_evidence_hash_from_dict(evidence_data)

                    # Step 3: Submit the complete hash to the blockchain
                    bc_result = blockchain.submit_evidence(complete_hash)

                    if bc_result.success:
                        results["blockchain_success"] = True
                        results["transaction_hash"] = bc_result.transaction_hash
                        results["block_number"] = bc_result.block_number
                        results["record_id"] = bc_result.record_id
                        results["evidence_hash"] = complete_hash
                        evidence_hash = complete_hash

                        # Step 4: Save file with complete evidence (hash matches on-chain)
                        evidence_data['evidence_hash'] = complete_hash
                        with open(evidence_path, 'w') as f:
                            json.dump(evidence_data, f, indent=2)

                        print_step(7, 7, "Blockchain transaction", "OK")
                        print()
                        print(f"   Transaction:")
                        print(f"   {bc_result.transaction_hash}")
                        print()
                        if blockchain.mode == "hardhat":
                            print("   Verified on local Hardhat blockchain (chain ID: 31337)")
                            print("   (No public explorer URL — local node only)")
                        else:
                            print(f"   View on Polygon Amoy:")
                            print(f"   https://amoy.polygonscan.com/tx/{bc_result.transaction_hash}")
                        print()
                        print("   STATUS: VERIFIED")
                    else:
                        # Original hash was committed; complete hash submission failed
                        results["blockchain_success"] = False
                        results["blockchain_error"] = f"Complete hash submission failed: {bc_result.error}"
                        print_step(7, 7, "Blockchain transaction", "FAIL")
                        print()
                        print(f"   Complete-hash submission failed: {bc_result.error}")
                        print(f"   Evidence preserved locally: {evidence_path}")
                else:
                    print_step(7, 7, "Blockchain transaction", "FAIL")
                    print()
                    print(f"   Transaction failed: {tx_result.error}")
                    print(f"   Evidence preserved locally: {evidence_path}")
                    results["blockchain_success"] = False
                    results["blockchain_error"] = tx_result.error

        except Exception as e:
            print_step(7, 7, "Blockchain transaction", "FAIL")
            print()
            print("   Blockchain transaction failed.")
            print(f"   Evidence preserved locally: {evidence_path}")
            logger.exception("Blockchain error")
            results["blockchain_success"] = False
            results["blockchain_error"] = str(e)

    # ============ Summary ============
    print()
    print("=" * 40)
    if results.get("match_found") and (results.get("blockchain_success") or skip_blockchain):
        print("       PIPELINE COMPLETED")
    else:
        print("       PIPELINE FINISHED")
    print("=" * 40)
    print()

    results["success"] = bool(results.get("match_found"))

    return results


def main():
    """Main entry point"""
    args = parse_arguments()

    # Set verbose logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Validate threshold
    if not 0.0 <= args.threshold <= 1.0:
        print("ERROR: Threshold must be between 0.0 and 1.0")
        sys.exit(1)

    # Run pipeline
    try:
        results = run_pipeline(
            image_path=args.image,
            threshold=args.threshold,
            output_path=args.output,
            max_candidates=args.max_candidates,
            skip_blockchain=args.skip_blockchain
        )

        # Exit with appropriate code
        sys.exit(0 if results.get("success") else 1)

    except KeyboardInterrupt:
        print("\n\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        logger.exception("Fatal error")
        sys.exit(1)


if __name__ == "__main__":
    main()
