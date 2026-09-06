"""
Face Detection and Encoding Module

Uses InsightFace with the ArcFace model for face detection and embedding generation.
Provides robust face recognition capabilities for the FaceTrace pipeline.
"""

import os
import sys
import logging
import warnings
import numpy as np
import cv2
from typing import Optional, Tuple, List
from dataclasses import dataclass

# Suppress noisy library warnings
warnings.filterwarnings('ignore', category=FutureWarning)
logging.getLogger('insightface').setLevel(logging.ERROR)

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class FaceResult:
    """Result of face detection and encoding"""
    embedding: np.ndarray
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    age: Optional[int] = None
    gender: Optional[str] = None

    def get_embedding_hex(self) -> str:
        """Get embedding as hex string (for blockchain storage)"""
        return self.embedding.tobytes().hex()


class FaceEncoder:
    """
    Face detection and encoding using InsightFace with ArcFace model.

    This class provides methods to:
    1. Detect faces in images
    2. Generate face embeddings using ArcFace
    3. Compare face embeddings using cosine similarity
    """

    def __init__(self, model_name: str = "buffalo_l", device: str = "cpu"):
        """
        Initialize the face encoder.

        Args:
            model_name: InsightFace model pack name (default: buffalo_l)
            device: Device to run inference on (cpu or cuda)
        """
        self.model_name = model_name
        self.device = device
        self.app = None
        self._initialized = False

    def initialize(self) -> None:
        """Lazy initialization of the InsightFace model"""
        if self._initialized:
            return

        try:
            from insightface.app import FaceAnalysis

            logger.info(f"Loading InsightFace model: {self.model_name}")
            self.app = FaceAnalysis(
                name=self.model_name,
                providers=["CPUExecutionProvider"] if self.device == "cpu" else ["CUDAExecutionProvider"]
            )
            self.app.prepare(ctx_id=0 if self.device == "cuda" else -1, det_size=(640, 640))
            self._initialized = True
            logger.info("InsightFace model loaded successfully")
        except ImportError:
            logger.error("InsightFace not installed. Install with: pip install insightface")
            self._handle_missing_insightface()
        except Exception as e:
            logger.error(f"Error loading InsightFace model: {e}")
            raise

    def _handle_missing_insightface(self) -> None:
        """
        Fallback implementation using OpenCV DNN when InsightFace is not available.
        Uses a pre-trained Caffe model for face detection.
        """
        logger.warning("Using OpenCV DNN face detector as fallback")
        try:
            # Try to use OpenCV's built-in face detector
            self.app = cv2.dnn.readNetFromCaffe(
                cv2.data.haarcascades + "deploy.prototxt" if os.path.exists(cv2.data.haarcascades + "deploy.prototxt") else "",
                ""
            )
        except Exception:
            # Use Haar cascade as last resort
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(cascade_path):
                self.app = cv2.CascadeClassifier(cascade_path)
            else:
                raise RuntimeError("No face detection model available. Please install insightface.")

    def load_image(self, image_path: str) -> np.ndarray:
        """
        Load an image from disk.

        Args:
            image_path: Path to the image file

        Returns:
            Image as numpy array in BGR format

        Raises:
            FileNotFoundError: If image doesn't exist
            ValueError: If image cannot be loaded
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Could not load image: {image_path}")
        return img

    def detect_face(self, image_path: str) -> FaceResult:
        """
        Detect the primary face in an image and generate its embedding.

        Args:
            image_path: Path to the image file

        Returns:
            FaceResult with embedding and metadata

        Raises:
            ValueError: If no face or multiple faces detected
        """
        if not self._initialized:
            self.initialize()

        img = self.load_image(image_path)

        # Detect faces using InsightFace
        faces = self.app.get(img)

        if len(faces) == 0:
            raise ValueError("No face detected. Pipeline terminated.")

        if len(faces) > 1:
            # Return the largest face (by bounding box area)
            largest_face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
            logger.warning(f"Multiple faces detected ({len(faces)}). Using the largest one.")
            face = largest_face
        else:
            face = faces[0]

        # Extract face data
        bbox = tuple(int(v) for v in face.bbox)
        embedding = face.normed_embedding if hasattr(face, 'normed_embedding') else face.embedding
        # Normalize the embedding
        embedding = embedding / np.linalg.norm(embedding)

        # Extract optional attributes
        age = int(face.age) if hasattr(face, 'age') and face.age is not None else None
        gender = None
        if hasattr(face, 'gender'):
            gender = "Male" if face.gender == 1 else "Female"

        confidence = float(face.det_score) if hasattr(face, 'det_score') else 1.0

        return FaceResult(
            embedding=embedding,
            bbox=bbox,
            confidence=confidence,
            age=age,
            gender=gender
        )

    def detect_face_from_array(self, img_array: np.ndarray) -> Optional[FaceResult]:
        """
        Detect face from a numpy array (useful for candidate images).

        Args:
            img_array: Image as numpy array (BGR format)

        Returns:
            FaceResult if face found, None otherwise
        """
        if not self._initialized:
            self.initialize()

        if img_array is None or img_array.size == 0:
            return None

        try:
            faces = self.app.get(img_array)

            if len(faces) == 0:
                return None

            # Use the largest face
            face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))

            bbox = tuple(int(v) for v in face.bbox)
            embedding = face.normed_embedding if hasattr(face, 'normed_embedding') else face.embedding
            embedding = embedding / np.linalg.norm(embedding)
            confidence = float(face.det_score) if hasattr(face, 'det_score') else 1.0

            return FaceResult(
                embedding=embedding,
                bbox=bbox,
                confidence=confidence
            )
        except Exception as e:
            logger.error(f"Error detecting face: {e}")
            return None

    def compute_similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """
        Compute cosine similarity between two face embeddings.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding

        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        # Ensure embeddings are normalized
        e1 = embedding1 / np.linalg.norm(embedding1)
        e2 = embedding2 / np.linalg.norm(embedding2)

        # Cosine similarity
        similarity = np.dot(e1, e2)
        # Clamp to [0, 1]
        similarity = max(0.0, min(1.0, float(similarity)))
        return similarity

    def is_same_person(self, embedding1: np.ndarray, embedding2: np.ndarray, threshold: float = 0.75) -> Tuple[bool, float]:
        """
        Determine if two embeddings represent the same person.

        Args:
            embedding1: First face embedding
            embedding2: Second face embedding
            threshold: Similarity threshold for match

        Returns:
            Tuple of (is_match, similarity_score)
        """
        similarity = self.compute_similarity(embedding1, embedding2)
        return (similarity >= threshold, similarity)


def get_face_encoder() -> FaceEncoder:
    """
    Factory function to get a FaceEncoder instance.
    Uses caching to avoid reloading the model.
    """
    if not hasattr(get_face_encoder, '_instance'):
        get_face_encoder._instance = FaceEncoder()
        get_face_encoder._instance.initialize()
    return get_face_encoder._instance
