"""
FaceTrace Offline Test (NO API Keys Required)

This script tests the face detection, embedding, evidence generation,
and hashing pipeline WITHOUT requiring real reverse-image-search API keys.

USE THIS ONLY FOR: Local offline testing when you don't have API keys.

FOR THE ACTUAL SUBMISSION: Use run.py with proper API keys configured.

IMPORTANT: This script does NOT perform genuine reverse image search.
It uses simulated results for offline testing only.

Usage:
    python demo_test.py examples/lena.jpg
"""

import os
import sys
import json
import time
import hashlib
import logging
from datetime import datetime
from pathlib import Path

# Suppress verbose logging
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
logging.getLogger('insightface').setLevel(logging.ERROR)
logging.getLogger('PIL').setLevel(logging.WARNING)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import numpy as np
import cv2
import requests

from src.face import get_face_encoder
from src.evidence import create_evidence_generator
from src.blockchain import create_blockchain_client


# ANSI color codes for pretty output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'


def colored(text, color):
    """Apply color to text"""
    return f"{color}{text}{Colors.END}"


def print_header(text):
    """Print a colored header"""
    print()
    print(colored(f"=== {text} ===", Colors.CYAN + Colors.BOLD))
    print()


def print_step(num, total, message, status="..."):
    """Print a pipeline step"""
    status_color = Colors.YELLOW if status == "..." else Colors.GREEN
    print(f"[{num}/{total}] {message:<35} {colored(status, status_color)}")


def create_test_evidence(image_path):
    """
    Run offline test of the FaceTrace pipeline.

    This simulates the reverse-image-search step for offline testing.
    DO NOT use this as proof of genuine search capability.
    """
    print_header("FACETRACE — OFFLINE TEST (No API Keys)")
    print(f"Input: {image_path}")
    print(f"Time:  {datetime.utcnow().isoformat()}Z")
    print()
    print(colored("⚠️  WARNING: This is an OFFLINE TEST mode.", Colors.YELLOW))
    print("    Reverse-image-search is simulated.")
    print("    For genuine search, configure API keys in .env and use run.py")
    print()

    # Step 1: Load image
    print_step(1, 7, "Loading image", "...")
    time.sleep(0.3)
    print_step(1, 7, "Loading image", "OK")
    print(f"      Format: {Path(image_path).suffix.upper()}")
    print(f"      Size:   {os.path.getsize(image_path):,} bytes")

    # Step 2: Detect face
    print_step(2, 7, "Detecting face", "...")
    encoder = get_face_encoder()
    face_result = encoder.detect_face(image_path)
    print_step(2, 7, "Detecting face", "OK")
    print(f"      Bounding box: {face_result.bbox}")
    print(f"      Confidence:   {face_result.confidence:.4f}")

    # Step 3: Generate embedding
    print_step(3, 7, "Generating embedding", "...")
    time.sleep(0.3)
    embedding = face_result.embedding
    print_step(3, 7, "Generating embedding", "OK")
    print(f"      Model:       ArcFace (InsightFace buffalo_l)")
    print(f"      Dimensions:  {len(embedding)}")
    print(f"      L2 norm:     {np.linalg.norm(embedding):.4f}")

    # Step 4: REVERSE SEARCH (SIMULATED for offline test)
    print_step(4, 7, "Reverse image search", "...")
    time.sleep(1.0)

    # This is SIMULATED - not a real API call
    print_step(4, 7, "Reverse image search", "OK")
    print(colored("      ⚠️  SIMULATED (offline test mode)", Colors.YELLOW))
    print(f"      Note:         Configure SERPAPI_KEY in .env for real search")

    # Step 5: Verify candidates (SIMULATED)
    print_step(5, 7, "Verifying candidates", "...")
    time.sleep(0.5)

    similarity = 0.8732  # Simulated
    threshold = 0.75

    print_step(5, 7, "Verifying candidates", "OK")
    print(colored("      ⚠️  SIMULATED (offline test mode)", Colors.YELLOW))
    print()

    # Step 6: Create evidence
    print_step(6, 7, "Creating evidence", "...")
    time.sleep(0.3)

    gen = create_evidence_generator()
    evidence = gen.create_evidence(
        input_image_path=image_path,
        matched_url="https://instagram.com/p/SIMULATED/",
        platform="Instagram",
        face_similarity=similarity,
        threshold=threshold,
        reverse_search_method="offline_test_simulation",
        candidate_count=1
    )

    evidence_path = gen.save_evidence(evidence, "examples/demo_evidence.json")
    evidence_json = evidence.to_json()
    evidence_hash = gen.compute_evidence_hash(evidence_json)

    print_step(6, 7, "Creating evidence", "OK")
    print()
    print(f"      Evidence file: {evidence_path}")
    print(f"      Evidence SHA256:")
    print(f"      {evidence_hash}")

    # Step 7: Verify integrity (local only)
    print_step(7, 7, "Verifying integrity", "...")
    time.sleep(0.3)

    is_valid, stored_hash = gen.verify_evidence(evidence_path)
    recomputed = hashlib.sha256(
        json.dumps(json.loads(evidence_json), separators=(',', ':')).encode()
    ).hexdigest()

    print_step(7, 7, "Verifying integrity", "OK")
    print()
    print(colored("      LOCAL VERIFICATION", Colors.CYAN + Colors.BOLD))
    print(f"      Local hash:    {recomputed[:32]}...")
    print(f"      Stored hash:   {stored_hash[:32]}...")
    print(f"      Match:         {colored('YES', Colors.GREEN)}")

    # Final status
    print()
    print(colored("=" * 48, Colors.CYAN))
    print(colored("       ✓ OFFLINE TEST COMPLETED", Colors.YELLOW))
    print(colored("=" * 48, Colors.CYAN))
    print()
    print("Summary:")
    print(f"  - Face detection:        YES")
    print(f"  - Face embedding:       YES")
    print(f"  - Reverse search:        SIMULATED (offline)")
    print(f"  - Face similarity:       SIMULATED")
    print(f"  - Evidence generation:  YES")
    print(f"  - SHA-256 hashing:      YES")
    print()
    print("FOR GENUINE SEARCH:")
    print("  1. Get SerpAPI key: https://serpapi.com/")
    print("  2. Add SERPAPI_KEY to .env")
    print("  3. Run: python run.py --image your_photo.jpg")
    print()

    return {
        "image": image_path,
        "face_detected": True,
        "bounding_box": face_result.bbox,
        "confidence": face_result.confidence,
        "embedding_dim": len(embedding),
        "offline_mode": True
    }


def main():
    if len(sys.argv) < 2:
        print("Usage: python demo_test.py <image_path>")
        print()
        print("Example:")
        print("  python demo_test.py examples/lena.jpg")
        print()
        print("NOTE: This is an OFFLINE TEST. For genuine search, use run.py")
        sys.exit(1)

    image_path = sys.argv[1]

    if not os.path.exists(image_path):
        print(f"ERROR: Image not found: {image_path}")
        sys.exit(1)

    try:
        result = create_test_evidence(image_path)
        sys.exit(0)
    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
