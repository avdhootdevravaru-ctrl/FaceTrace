"""
Face Similarity Verifier Module

Verifies candidate images from reverse search results by comparing
face embeddings. This provides independent verification that the
discovered social media image contains the same person.
"""

import os
import io
import logging
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import cv2
import requests
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of verifying a candidate image"""
    url: str
    platform: Optional[str]
    face_detected: bool
    similarity: float
    threshold: float
    verified: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "url": self.url,
            "platform": self.platform,
            "face_detected": self.face_detected,
            "face_similarity": round(self.similarity, 4),
            "verification_threshold": self.threshold,
            "verified": self.verified,
            "error": self.error
        }


class CandidateVerifier:
    """
    Verifies candidate images from reverse search results.

    This class:
    1. Downloads candidate images from URLs
    2. Detects faces in candidate images
    3. Compares face embeddings with the input face
    4. Determines if the candidate is a verified match
    """

    def __init__(
        self,
        face_encoder,
        threshold: float = 0.75,
        timeout: int = 30,
        max_image_size: int = 2048
    ):
        """
        Initialize the candidate verifier.

        Args:
            face_encoder: FaceEncoder instance for face detection/embedding
            threshold: Minimum similarity for a match
            timeout: HTTP request timeout in seconds
            max_image_size: Maximum image dimension to download
        """
        self.face_encoder = face_encoder
        self.threshold = threshold
        self.timeout = timeout
        self.max_image_size = max_image_size

    def download_image(self, url: str) -> Optional[np.ndarray]:
        """
        Download an image from a URL.

        Args:
            url: Image URL to download

        Returns:
            Image as numpy array (BGR format) or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }

            response = requests.get(url, headers=headers, timeout=self.timeout, stream=True)
            response.raise_for_status()

            # Check content type
            content_type = response.headers.get('content-type', '').lower()
            if 'image' not in content_type and not any(
                url.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']
            ):
                logger.debug(f"Skipping non-image URL: {url}")
                return None

            # Read image data
            image_data = response.content

            # Convert to numpy array
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if img is None:
                # Try with PIL
                pil_img = Image.open(io.BytesIO(image_data))
                pil_img = pil_img.convert('RGB')
                img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)

            # Resize if too large
            h, w = img.shape[:2]
            if max(h, w) > self.max_image_size:
                scale = self.max_image_size / max(h, w)
                img = cv2.resize(img, None, fx=scale, fy=scale)

            return img

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout downloading: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error for {url}: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error downloading {url}: {e}")
            return None

    def verify_candidate(
        self,
        candidate_url: str,
        input_embedding: np.ndarray,
        image_url: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify a candidate image against the input face.

        Args:
            candidate_url: URL of the candidate page (used for platform detection and evidence).
            input_embedding: Face embedding from the input image.
            image_url: Direct publicly accessible image URL to download from.
                       When provided (e.g. from SerpAPI metadata), this takes precedence
                       over candidate_url for downloading, as social-media page URLs are
                       often login-gated.

        Returns:
            VerificationResult with match status
        """
        from .reverse_search import ReverseImageSearcher

        # Detect platform from the page URL
        searcher = ReverseImageSearcher()
        platform = searcher.detect_platform(candidate_url)

        # Download candidate image: prefer the direct image_url, fall back to page URL
        download_url = image_url or candidate_url
        img = self.download_image(download_url)

        if img is None:
            # If download failed, return rejected
            # In demo mode, we accept as a soft match
            logger.warning(f"Could not download candidate: {candidate_url}")

            return VerificationResult(
                url=candidate_url,
                platform=platform,
                face_detected=False,
                similarity=0.0,
                threshold=self.threshold,
                verified=False,
                error="Failed to download image"
            )

        # Detect face in candidate
        face_result = self.face_encoder.detect_face_from_array(img)

        if face_result is None:
            return VerificationResult(
                url=candidate_url,
                platform=platform,
                face_detected=False,
                similarity=0.0,
                threshold=self.threshold,
                verified=False,
                error="No detectable face in candidate image"
            )

        # Compute similarity
        similarity = self.face_encoder.compute_similarity(
            input_embedding,
            face_result.embedding
        )

        # Determine if verified
        verified = similarity >= self.threshold

        if verified:
            logger.info(f"VERIFIED: {candidate_url} (similarity: {similarity:.4f})")
        else:
            logger.info(f"REJECTED: {candidate_url} (similarity: {similarity:.4f})")

        return VerificationResult(
            url=candidate_url,
            platform=platform,
            face_detected=True,
            similarity=similarity,
            threshold=self.threshold,
            verified=verified
        )

    def verify_candidates(
        self,
        candidates: List[str],
        input_embedding: np.ndarray,
        image_urls: Optional[List[Optional[str]]] = None
    ) -> List[VerificationResult]:
        """
        Verify multiple candidate images.

        Args:
            candidates: List of candidate page URLs (used for evidence and platform detection).
            input_embedding: Face embedding from the input image.
            image_urls: Optional list of direct image URLs (from SerpAPI metadata) to use for
                        downloading instead of the page URLs. Must be same length as candidates.
                        Pass None for any position to fall back to the page URL.

        Returns:
            List of VerificationResult sorted by similarity
        """
        results = []

        for i, url in enumerate(candidates):
            img_url = image_urls[i] if image_urls and i < len(image_urls) else None
            result = self.verify_candidate(url, input_embedding, image_url=img_url)
            results.append(result)

        # Sort by similarity (highest first)
        results.sort(key=lambda r: r.similarity, reverse=True)

        return results

    def find_best_match(
        self,
        candidates: List[str],
        input_embedding: np.ndarray,
        image_urls: Optional[List[Optional[str]]] = None
    ) -> Optional[VerificationResult]:
        """
        Find the best matching candidate.

        Args:
            candidates: List of candidate page URLs (used for evidence and platform detection).
            input_embedding: Face embedding from the input image.
            image_urls: Optional list of direct image URLs (from SerpAPI metadata) to use for
                        downloading instead of the page URLs.

        Returns:
            Best VerificationResult or None if no match
        """
        results = self.verify_candidates(candidates, input_embedding, image_urls=image_urls)

        # Return first verified result (already sorted by similarity)
        for result in results:
            if result.verified:
                return result

        # If no verified result, return the best attempt
        if results:
            return results[0]

        return None


def create_verifier(face_encoder, threshold: float = 0.75) -> CandidateVerifier:
    """Factory function to create a CandidateVerifier instance"""
    return CandidateVerifier(face_encoder=face_encoder, threshold=threshold)
