"""
Evidence Generation Module

Generates tamper-evident evidence records for face verification results.
Creates JSON evidence files with cryptographic hashes for blockchain anchoring.

IMPORTANT: This module generates cryptographic commitments that are
stored on-chain. The evidence record contains:
- Input image hash (SHA-256 of file)
- Matched image hash
- Discovered URL
- Platform information
- Face similarity scores
- Timestamps

What is NOT stored on-chain:
- Original photographs
- Face embeddings/biometrics
- Private content
"""

import os
import json
import hashlib
import logging
from typing import Optional, Dict, Any, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class EvidenceRecord:
    """
    Evidence record for a face verification.
    This record is hashed and committed to the blockchain.
    """
    # Image hashes
    input_image_hash: str
    matched_image_hash: str

    # Discovery information
    matched_url: str
    platform: str

    # Verification results
    face_similarity: float
    verification_threshold: float
    verification_status: str  # "MATCH", "NO_MATCH", "FAILED"

    # Metadata
    timestamp: str
    pipeline_version: str = "1.0.0"

    # Additional context (optional)
    reverse_search_method: str = "unknown"
    candidate_count: int = 0
    record_id: Optional[int] = None
    blockchain_tx: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)


class EvidenceGenerator:
    """
    Generates evidence records for face verification results.

    The evidence record is used to create a cryptographic hash that
    is committed to the blockchain, providing tamper-evident proof
    of the verification result.
    """

    def __init__(self, pipeline_version: str = "1.0.0"):
        """
        Initialize the evidence generator.

        Args:
            pipeline_version: Version of the FaceTrace pipeline
        """
        self.pipeline_version = pipeline_version

    @staticmethod
    def compute_file_hash(file_path: str) -> str:
        """
        Compute SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            Hex-encoded SHA-256 hash
        """
        sha256 = hashlib.sha256()

        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)

        return sha256.hexdigest()

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """
        Compute SHA-256 hash of string content.

        Args:
            content: String content to hash

        Returns:
            Hex-encoded SHA-256 hash
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_evidence_hash_from_dict(evidence_dict: Dict[str, Any]) -> str:
        """
        Compute SHA-256 hash of an evidence dict using canonical JSON serialization.

        This is the single canonical method for computing the evidence hash.
        Uses deterministic field ordering so that run.py, verify.py, and any
        other tool always produce identical hashes for the same data.

        Args:
            evidence_dict: Dictionary of evidence fields (MUST NOT contain
                           'evidence_hash' key — that field is the output, not input).

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Remove any stray evidence_hash key (shouldn't be present, but be safe)
        working = {k: v for k, v in evidence_dict.items() if k != 'evidence_hash'}
        # Sort keys for canonical ordering (ensures dict iteration order cannot cause mismatch)
        normalized = json.dumps(working, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

    @staticmethod
    def compute_evidence_hash(evidence_json: str) -> str:
        """
        Compute SHA-256 hash of evidence JSON.

        This is the hash that gets committed to the blockchain.

        Args:
            evidence_json: JSON string of evidence record

        Returns:
            Hex-encoded SHA-256 hash
        """
        # Delegate to canonical dict-based method for consistent behavior
        return EvidenceGenerator.compute_evidence_hash_from_dict(
            json.loads(evidence_json)
        )

    def create_evidence(
        self,
        input_image_path: str,
        matched_url: str,
        platform: str,
        face_similarity: float,
        threshold: float,
        reverse_search_method: str = "unknown",
        candidate_count: int = 1,
        matched_image_hash: Optional[str] = None
    ) -> EvidenceRecord:
        """
        Create an evidence record for a verified match.

        Args:
            input_image_path: Path to input image
            matched_url: Discovered social media URL
            platform: Platform name (Instagram, Twitter, etc.)
            face_similarity: Calculated similarity score
            threshold: Verification threshold used
            reverse_search_method: Method used for reverse search
            candidate_count: Number of candidates evaluated
            matched_image_hash: Hash of the matched image (if available)

        Returns:
            EvidenceRecord instance
        """
        # Compute input image hash
        input_hash = self.compute_file_hash(input_image_path)

        # Generate timestamp
        timestamp = datetime.utcnow().isoformat() + "Z"

        # Determine verification status
        if face_similarity >= threshold:
            status = "MATCH"
        else:
            status = "NO_MATCH"

        # Create evidence record
        evidence = EvidenceRecord(
            input_image_hash=input_hash,
            matched_image_hash=matched_image_hash or "unavailable",
            matched_url=matched_url,
            platform=platform,
            face_similarity=round(face_similarity, 4),
            verification_threshold=threshold,
            verification_status=status,
            timestamp=timestamp,
            pipeline_version=self.pipeline_version,
            reverse_search_method=reverse_search_method,
            candidate_count=candidate_count
        )

        return evidence

    def save_evidence(
        self,
        evidence: EvidenceRecord,
        output_path: Optional[str] = None,
        include_hash: bool = True
    ) -> str:
        """
        Save evidence record to JSON file.

        Args:
            evidence: EvidenceRecord to save
            output_path: Output file path (auto-generated if None)
            include_hash: Include SHA-256 hash in output

        Returns:
            Path to saved evidence file
        """
        evidence_dict = evidence.to_dict()

        # Compute evidence hash from the complete evidence data using canonical method.
        # This hash must be computed from all evidence fields (excluding the hash itself)
        # so that verify.py can reproduce the identical hash from the saved file.
        evidence_hash = self.compute_evidence_hash_from_dict(evidence_dict)

        if include_hash:
            evidence_dict["evidence_hash"] = evidence_hash

        # Auto-generate filename if not provided
        if output_path is None:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            short_hash = evidence_hash[:8]
            output_path = f"evidence_{timestamp}_{short_hash}.json"

        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(evidence_dict, f, indent=2)

        logger.info(f"Evidence saved to: {output_path}")
        logger.info(f"Evidence SHA-256: {evidence_hash}")

        return output_path

    def load_evidence(self, evidence_path: str) -> EvidenceRecord:
        """
        Load evidence record from JSON file.

        Args:
            evidence_path: Path to evidence JSON file

        Returns:
            EvidenceRecord instance
        """
        with open(evidence_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        return EvidenceRecord(
            input_image_hash=data["input_image_hash"],
            matched_image_hash=data.get("matched_image_hash", ""),
            matched_url=data["matched_url"],
            platform=data["platform"],
            face_similarity=data["face_similarity"],
            verification_threshold=data["verification_threshold"],
            verification_status=data["verification_status"],
            timestamp=data["timestamp"],
            pipeline_version=data.get("pipeline_version", "1.0.0"),
            reverse_search_method=data.get("reverse_search_method", "unknown"),
            candidate_count=data.get("candidate_count", 0),
            record_id=data.get("record_id"),
            blockchain_tx=data.get("blockchain_tx")
        )

    def verify_evidence(self, evidence_path: str) -> Tuple[bool, str]:
        """
        Verify that evidence hasn't been tampered with.

        Recomputes the evidence hash using the canonical method and compares
        with the stored hash.

        Args:
            evidence_path: Path to evidence JSON file

        Returns:
            Tuple of (is_valid, stored_hash)
        """
        with open(evidence_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        stored_hash = data.get("evidence_hash", "")

        if not stored_hash:
            return (False, "")

        # Use the same canonical method as run.py and verify.py
        computed_hash = self.compute_evidence_hash_from_dict(data)

        is_valid = computed_hash == stored_hash

        return (is_valid, stored_hash)


def create_evidence_generator() -> EvidenceGenerator:
    """Factory function to create an EvidenceGenerator instance"""
    return EvidenceGenerator()
