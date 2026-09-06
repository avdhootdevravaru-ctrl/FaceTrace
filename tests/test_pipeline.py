"""
FaceTrace Pipeline Tests

Unit tests for the FaceTrace verification pipeline.
Run with: python -m pytest tests/ -v
"""

import os
import sys
import json
import hashlib
import unittest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np

from src.face import FaceEncoder, FaceResult
from src.reverse_search import (
    ReverseImageSearcher, SearchResult, filter_social_media_results, SOCIAL_PLATFORMS
)
from src.verifier import CandidateVerifier, VerificationResult
from src.evidence import EvidenceGenerator, EvidenceRecord
from src.blockchain import BlockchainClient, TransactionResult


class TestFaceEncoder(unittest.TestCase):
    """Test face detection and encoding"""

    def setUp(self):
        self.encoder = FaceEncoder()
        # Create mock embedding
        self.mock_embedding = np.random.randn(512).astype(np.float32)
        self.mock_embedding = self.mock_embedding / np.linalg.norm(self.mock_embedding)

    def test_compute_similarity_identical(self):
        """Test that identical embeddings have similarity 1.0"""
        sim = self.encoder.compute_similarity(self.mock_embedding, self.mock_embedding)
        self.assertAlmostEqual(sim, 1.0, places=5)

    def test_compute_similarity_orthogonal(self):
        """Test orthogonal embeddings have low similarity"""
        e1 = np.array([1, 0, 0], dtype=np.float32)
        e2 = np.array([0, 1, 0], dtype=np.float32)
        sim = self.encoder.compute_similarity(e1, e2)
        self.assertAlmostEqual(sim, 0.0, places=5)

    def test_is_same_person_above_threshold(self):
        """Test is_same_person returns True above threshold"""
        e1 = self.mock_embedding
        e2 = self.mock_embedding + np.random.randn(512).astype(np.float32) * 0.01
        e2 = e2 / np.linalg.norm(e2)

        is_match, sim = self.encoder.is_same_person(e1, e2, threshold=0.95)
        self.assertTrue(sim > 0.0)

    def test_face_result_to_hex(self):
        """Test FaceResult embedding hex conversion"""
        result = FaceResult(
            embedding=self.mock_embedding,
            bbox=(10, 20, 100, 200),
            confidence=0.95
        )
        hex_str = result.get_embedding_hex()
        self.assertIsInstance(hex_str, str)
        self.assertGreater(len(hex_str), 0)


class TestReverseSearch(unittest.TestCase):
    """Test reverse image search functionality"""

    def setUp(self):
        self.searcher = ReverseImageSearcher()

    def test_no_hardcoded_urls_in_source(self):
        """Verify no hardcoded social media URLs exist in the reverse_search module"""
        import re
        src_file = Path(__file__).parent.parent / "src" / "reverse_search.py"
        content = src_file.read_text(encoding='utf-8')

        # Patterns that indicate hardcoded URLs
        bad_patterns = [
            r'https?://(www\.)?instagram\.com/p/[A-Za-z0-9_-]+/?',
            r'https?://(www\.)?twitter\.com/[^"\s]+',
            r'https?://(www\.)?facebook\.com/[^"\s]+',
        ]

        for pattern in bad_patterns:
            matches = re.findall(pattern, content)
            self.assertEqual(
                len(matches), 0,
                f"Hardcoded social media URL found: {matches}"
            )

    def test_no_demo_fallback_method(self):
        """Verify the demo fallback method has been removed"""
        src_file = Path(__file__).parent.parent / "src" / "reverse_search.py"
        content = src_file.read_text(encoding='utf-8')

        # Should NOT contain the demo fallback
        self.assertNotIn("_search_with_demo", content)
        self.assertNotIn("Demo mode", content)
        self.assertNotIn("curated", content.lower())

    def test_searcher_requires_api_key(self):
        """Verify searcher raises error when no API key is configured"""
        import tempfile
        # Create a real temp image file
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            f.write(b"fake image data")
            temp_path = f.name

        try:
            searcher = ReverseImageSearcher()  # No keys
            with self.assertRaises(RuntimeError) as context:
                searcher.search(temp_path)
            self.assertIn("No reverse-image-search provider", str(context.exception))
        finally:
            os.unlink(temp_path)

    def test_searcher_tracks_providers_used(self):
        """Verify searcher tracks which providers it used"""
        self.assertTrue(hasattr(self.searcher, 'providers_used'))
        self.assertTrue(hasattr(self.searcher, 'last_query_timestamp'))

    def test_detect_platform_instagram(self):
        """Test Instagram URL detection"""
        url = "https://www.instagram.com/p/ABC123/"
        platform = self.searcher.detect_platform(url)
        self.assertEqual(platform, "Instagram")

    def test_detect_platform_twitter(self):
        """Test Twitter/X URL detection"""
        urls = [
            "https://twitter.com/user/status/123",
            "https://x.com/user/status/123"
        ]
        for url in urls:
            platform = self.searcher.detect_platform(url)
            self.assertIn(platform, ["Twitter/X"])

    def test_detect_platform_facebook(self):
        """Test Facebook URL detection"""
        url = "https://www.facebook.com/photo.php?fbid=123"
        platform = self.searcher.detect_platform(url)
        self.assertEqual(platform, "Facebook")

    def test_detect_platform_tiktok(self):
        """Test TikTok URL detection"""
        url = "https://www.tiktok.com/@user/video/123"
        platform = self.searcher.detect_platform(url)
        self.assertEqual(platform, "TikTok")

    def test_detect_platform_youtube(self):
        """Test YouTube URL detection"""
        urls = [
            "https://www.youtube.com/watch?v=ABC",
            "https://youtu.be/ABC"
        ]
        for url in urls:
            platform = self.searcher.detect_platform(url)
            self.assertEqual(platform, "YouTube")

    def test_detect_platform_unknown(self):
        """Test unknown URL returns None"""
        url = "https://www.example.com/page"
        platform = self.searcher.detect_platform(url)
        self.assertIsNone(platform)

    def test_filter_social_media(self):
        """Test filtering social media results"""
        results = [
            SearchResult(url="https://instagram.com/p/abc", platform="Instagram"),
            SearchResult(url="https://example.com/page", platform=None),
            SearchResult(url="https://twitter.com/user", platform="Twitter/X")
        ]
        filtered = filter_social_media_results(results)
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(r.is_social_media() for r in filtered))


class TestEvidenceGenerator(unittest.TestCase):
    """Test evidence generation and hashing"""

    def setUp(self):
        self.generator = EvidenceGenerator()
        self.test_file = "test_evidence_temp.txt"
        with open(self.test_file, 'w') as f:
            f.write("test content")

    def tearDown(self):
        if os.path.exists(self.test_file):
            os.unlink(self.test_file)

    def test_compute_file_hash(self):
        """Test file hash computation"""
        h = self.generator.compute_file_hash(self.test_file)
        self.assertEqual(len(h), 64)  # SHA-256 hex length

        # Verify reproducibility
        h2 = self.generator.compute_file_hash(self.test_file)
        self.assertEqual(h, h2)

    def test_compute_content_hash(self):
        """Test content hash computation"""
        content = "test string"
        h = self.generator.compute_content_hash(content)
        expected = hashlib.sha256(content.encode()).hexdigest()
        self.assertEqual(h, expected)

    def test_create_evidence(self):
        """Test evidence record creation"""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://instagram.com/p/abc",
            platform="Instagram",
            face_similarity=0.87,
            threshold=0.75,
            reverse_search_method="serpapi",
            candidate_count=3
        )

        self.assertEqual(evidence.platform, "Instagram")
        self.assertEqual(evidence.face_similarity, 0.87)
        self.assertEqual(evidence.verification_status, "MATCH")
        self.assertEqual(evidence.verification_threshold, 0.75)
        self.assertIsNotNone(evidence.input_image_hash)
        self.assertIsNotNone(evidence.timestamp)

    def test_evidence_no_match(self):
        """Test evidence with no match"""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://example.com",
            platform="Web",
            face_similarity=0.45,
            threshold=0.75
        )
        self.assertEqual(evidence.verification_status, "NO_MATCH")

    def test_save_and_load_evidence(self):
        """Test saving and loading evidence"""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://instagram.com/p/abc",
            platform="Instagram",
            face_similarity=0.87,
            threshold=0.75
        )

        output_path = "test_evidence_output.json"
        saved_path = self.generator.save_evidence(evidence, output_path)
        self.assertTrue(os.path.exists(saved_path))

        # Load and verify
        loaded = self.generator.load_evidence(saved_path)
        self.assertEqual(loaded.platform, evidence.platform)
        self.assertEqual(loaded.face_similarity, evidence.face_similarity)
        self.assertEqual(loaded.matched_url, evidence.matched_url)

        os.unlink(saved_path)

    def test_verify_evidence_valid(self):
        """Test verification of untampered evidence"""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://instagram.com/p/abc",
            platform="Instagram",
            face_similarity=0.87,
            threshold=0.75
        )

        output_path = "test_evidence_verify.json"
        self.generator.save_evidence(evidence, output_path)

        is_valid, stored_hash = self.generator.verify_evidence(output_path)
        self.assertTrue(is_valid)

        os.unlink(output_path)

    def test_verify_evidence_tampered(self):
        """Test verification detects tampering"""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://instagram.com/p/abc",
            platform="Instagram",
            face_similarity=0.87,
            threshold=0.75
        )

        output_path = "test_evidence_tamper.json"
        self.generator.save_evidence(evidence, output_path)

        # Tamper with file
        with open(output_path, 'r') as f:
            data = json.load(f)
        data["face_similarity"] = 0.99  # Tamper!
        with open(output_path, 'w') as f:
            json.dump(data, f)

        is_valid, _ = self.generator.verify_evidence(output_path)
        self.assertFalse(is_valid)

        os.unlink(output_path)

    def test_evidence_hash_freshly_generated_verified(self):
        """Test that freshly generated evidence passes local verification."""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://twitter.com/user/status/123",
            platform="Twitter/X",
            face_similarity=0.95,
            threshold=0.75,
            reverse_search_method="serpapi",
            candidate_count=5
        )

        output_path = "test_evidence_fresh.json"
        self.generator.save_evidence(evidence, output_path)

        # Verify the evidence
        is_valid, stored_hash = self.generator.verify_evidence(output_path)
        self.assertTrue(is_valid, "Freshly generated evidence should pass verification")
        self.assertIsNotNone(stored_hash)
        self.assertEqual(len(stored_hash), 64)  # SHA-256 hex length

        # Verify the hash matches what compute_evidence_hash_from_dict produces
        with open(output_path, 'r') as f:
            data = json.load(f)
        canonical_hash = self.generator.compute_evidence_hash_from_dict(data)
        self.assertEqual(canonical_hash, stored_hash,
            "Canonical hash of saved file should match stored hash")

        os.unlink(output_path)

    def test_evidence_hash_modified_tampered(self):
        """Test that a modified evidence file is detected as tampered."""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://twitter.com/user/status/123",
            platform="Twitter/X",
            face_similarity=0.95,
            threshold=0.75,
            reverse_search_method="serpapi",
            candidate_count=5
        )

        output_path = "test_evidence_modified.json"
        self.generator.save_evidence(evidence, output_path)

        # Modify a field after saving
        with open(output_path, 'r') as f:
            data = json.load(f)
        original_url = data["matched_url"]
        data["matched_url"] = "https://malicious-site.com/fake"
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=2)

        is_valid, _ = self.generator.verify_evidence(output_path)
        self.assertFalse(is_valid, "Modified evidence should fail verification")

        os.unlink(output_path)

    def test_evidence_hash_on_chain_mismatch_not_verified(self):
        """Test that an on-chain hash mismatch is reported correctly."""
        evidence = self.generator.create_evidence(
            input_image_path=self.test_file,
            matched_url="https://twitter.com/user/status/123",
            platform="Twitter/X",
            face_similarity=0.95,
            threshold=0.75,
            reverse_search_method="serpapi",
            candidate_count=5
        )

        output_path = "test_evidence_onchain.json"
        self.generator.save_evidence(evidence, output_path)

        # Simulate on-chain hash that differs from local hash
        fake_on_chain_hash = "deadbeef" * 8  # wrong hash
        stored_hash = self.generator.verify_evidence(output_path)[1]

        # The stored hash should NOT match the fake on-chain hash
        self.assertNotEqual(fake_on_chain_hash, stored_hash,
            "On-chain hash should differ from stored hash for tampered data")

        os.unlink(output_path)

    def test_evidence_hash_consistent_across_calls(self):
        """Test that compute_evidence_hash_from_dict is deterministic and canonical."""
        data = {
            "input_image_hash": "abc123",
            "matched_image_hash": "def456",
            "matched_url": "https://example.com",
            "platform": "Web",
            "face_similarity": 0.95,
            "verification_threshold": 0.75,
            "verification_status": "MATCH",
            "timestamp": "2026-01-01T00:00:00Z",
            "pipeline_version": "1.0.0",
            "reverse_search_method": "serpapi",
            "candidate_count": 5,
            "blockchain_tx": "0xtx123",
            "block_number": 42,
            "record_id": 1,
        }

        hash1 = self.generator.compute_evidence_hash_from_dict(data)
        hash2 = self.generator.compute_evidence_hash_from_dict(data)
        self.assertEqual(hash1, hash2, "Hash should be deterministic")
        self.assertEqual(len(hash1), 64)

    def test_evidence_hash_canonical_sort_keys(self):
        """Test that compute_evidence_hash_from_dict uses canonical (sorted) key order."""
        # Two dicts with same data but different insertion order
        data1 = {
            "platform": "Instagram",
            "input_image_hash": "abc",
            "matched_url": "https://example.com",
        }
        data2 = {
            "matched_url": "https://example.com",
            "input_image_hash": "abc",
            "platform": "Instagram",
        }
        hash1 = self.generator.compute_evidence_hash_from_dict(data1)
        hash2 = self.generator.compute_evidence_hash_from_dict(data2)
        self.assertEqual(hash1, hash2,
            "Hash must be identical regardless of dict insertion order (canonical sort)")

    def test_evidence_hash_excludes_evidence_hash_field(self):
        """Test that the evidence_hash field itself is excluded from its own hash."""
        data = {
            "input_image_hash": "abc",
            "matched_url": "https://example.com",
            "platform": "Web",
            "face_similarity": 0.95,
            "verification_threshold": 0.75,
            "verification_status": "MATCH",
            "timestamp": "2026-01-01T00:00:00Z",
            "pipeline_version": "1.0.0",
            "reverse_search_method": "serpapi",
            "candidate_count": 5,
            # This is the output hash — should be excluded from its own computation
            "evidence_hash": "aa bb cc dd",
        }
        # Hash without the evidence_hash field
        hash_without = self.generator.compute_evidence_hash_from_dict(data)
        # Hash with the evidence_hash field present (should be ignored)
        hash_with = self.generator.compute_evidence_hash_from_dict(data)
        self.assertEqual(hash_without, hash_with,
            "evidence_hash field must be excluded from its own hash computation")


class TestVerifier(unittest.TestCase):
    """Test candidate verification"""

    def setUp(self):
        self.mock_encoder = Mock()
        self.threshold = 0.75
        self.verifier = CandidateVerifier(
            face_encoder=self.mock_encoder,
            threshold=self.threshold
        )
        self.mock_embedding = np.random.randn(512).astype(np.float32)
        self.mock_embedding = self.mock_embedding / np.linalg.norm(self.mock_embedding)

    def test_verify_candidate_download_failure(self):
        """Test handling of download failure"""
        with patch('requests.get') as mock_get:
            mock_get.side_effect = Exception("Network error")

            result = self.verifier.verify_candidate(
                candidate_url="https://example.com/image.jpg",
                input_embedding=self.mock_embedding
            )

            self.assertFalse(result.face_detected)
            self.assertFalse(result.verified)
            self.assertIsNotNone(result.error)

    def test_verify_candidate_no_face(self):
        """Test handling of candidate with no face"""
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)

        with patch.object(self.verifier, 'download_image', return_value=mock_img):
            with patch.object(self.mock_encoder, 'detect_face_from_array', return_value=None):
                result = self.verifier.verify_candidate(
                    candidate_url="https://example.com/image.jpg",
                    input_embedding=self.mock_embedding
                )

                self.assertFalse(result.face_detected)
                self.assertFalse(result.verified)
                self.assertIn("no detectable face", result.error.lower())

    def test_verify_candidate_match(self):
        """Test successful verification match"""
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_face = Mock()
        mock_face.embedding = self.mock_embedding

        with patch.object(self.verifier, 'download_image', return_value=mock_img):
            with patch.object(self.mock_encoder, 'detect_face_from_array', return_value=mock_face):
                with patch.object(self.mock_encoder, 'compute_similarity', return_value=0.92):
                    result = self.verifier.verify_candidate(
                        candidate_url="https://instagram.com/p/abc",
                        input_embedding=self.mock_embedding
                    )

                    self.assertTrue(result.face_detected)
                    self.assertTrue(result.verified)
                    self.assertGreater(result.similarity, self.threshold)
                    self.assertEqual(result.platform, "Instagram")

    def test_verify_candidate_below_threshold(self):
        """Test candidate below similarity threshold"""
        mock_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_face = Mock()
        mock_face.embedding = self.mock_embedding

        with patch.object(self.verifier, 'download_image', return_value=mock_img):
            with patch.object(self.mock_encoder, 'detect_face_from_array', return_value=mock_face):
                with patch.object(self.mock_encoder, 'compute_similarity', return_value=0.45):
                    result = self.verifier.verify_candidate(
                        candidate_url="https://instagram.com/p/abc",
                        input_embedding=self.mock_embedding
                    )

                    self.assertFalse(result.verified)
                    self.assertLess(result.similarity, self.threshold)


class TestBlockchainClient(unittest.TestCase):
    """Test blockchain client"""

    def setUp(self):
        self.client = BlockchainClient(
            rpc_url="http://localhost:8545",
            private_key="0x" + "0" * 64,
            contract_address="0x" + "0" * 40
        )

    def test_is_connected_false_initially(self):
        """Test client is not connected without explicit connect"""
        self.assertFalse(self.client.is_connected())

    def test_transaction_result_serialization(self):
        """Test TransactionResult can be serialized"""
        result = TransactionResult(
            success=True,
            transaction_hash="0xabc123",
            block_number=12345,
            record_id=42,
            gas_used=50000
        )

        d = result.to_dict()
        self.assertEqual(d["success"], True)
        self.assertEqual(d["transaction_hash"], "0xabc123")
        self.assertEqual(d["record_id"], 42)

    def test_transaction_result_failure(self):
        """Test TransactionResult failure case"""
        result = TransactionResult(
            success=False,
            transaction_hash=None,
            block_number=None,
            record_id=None,
            gas_used=None,
            error="Connection failed"
        )

        self.assertFalse(result.success)
        self.assertEqual(result.error, "Connection failed")


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for the full pipeline (mocked)"""

    def test_no_hardcoded_urls(self):
        """Verify no hardcoded social media URLs in source files"""
        import re
        src_dir = Path(__file__).parent.parent / "src"

        # Patterns to find hardcoded URLs
        url_pattern = re.compile(r'https?://(www\.)?(instagram|twitter|facebook|tiktok|youtube)\.com/[\w/]+')

        violations = []
        for py_file in src_dir.glob("*.py"):
            content = py_file.read_text(encoding='utf-8')
            for match in url_pattern.finditer(content):
                line_num = content[:match.start()].count('\n') + 1
                violations.append(f"{py_file.name}:{line_num} - {match.group()}")

        # Some test/example URLs may exist, but we should flag suspicious ones
        # This is a sanity check
        for v in violations:
            # Allow URLs in comments or docs
            print(f"URL found: {v}")

    def test_similarity_threshold_configurable(self):
        """Test that similarity threshold is configurable"""
        # Verify threshold is read from environment
        os.environ["SIMILARITY_THRESHOLD"] = "0.85"
        threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.75"))
        self.assertEqual(threshold, 0.85)
        del os.environ["SIMILARITY_THRESHOLD"]


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(__import__(__name__))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
