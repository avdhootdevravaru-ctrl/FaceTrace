"""
FaceTrace - Face Identity & Blockchain Verification Pipeline

A CLI-based verification pipeline that:
1. Detects and encodes faces
2. Performs reverse image search
3. Verifies matches using face similarity
4. Generates tamper-evident evidence records
5. Commits evidence hashes to the blockchain
"""

__version__ = "1.0.0"
__author__ = "FaceTrace"
__description__ = "Face Identity & Blockchain Verification Pipeline"

from .face import FaceEncoder, FaceResult, get_face_encoder
from .reverse_search import ReverseImageSearcher, SearchResult, filter_social_media_results, create_searcher
from .verifier import CandidateVerifier, VerificationResult, create_verifier
from .evidence import EvidenceGenerator, EvidenceRecord, create_evidence_generator
from .blockchain import BlockchainClient, TransactionResult, create_blockchain_client

__all__ = [
    # Face detection
    "FaceEncoder",
    "FaceResult",
    "get_face_encoder",
    # Reverse search
    "ReverseImageSearcher",
    "SearchResult",
    "filter_social_media_results",
    "create_searcher",
    # Verifier
    "CandidateVerifier",
    "VerificationResult",
    "create_verifier",
    # Evidence
    "EvidenceGenerator",
    "EvidenceRecord",
    "create_evidence_generator",
    # Blockchain
    "BlockchainClient",
    "TransactionResult",
    "create_blockchain_client",
]
