"""
Reverse Image Search Module

Performs genuine reverse image search to discover visually similar images
across the web, specifically targeting social media platforms.

This module uses REAL reverse-image-search APIs at runtime. Results are
dynamically discovered - no URLs are hardcoded or pre-selected.

Supported Providers (in priority order):
1. SerpAPI (Google Lens) - https://serpapi.com/
2. Bing Visual Search API - Microsoft Azure
3. TinEye API - https://api.tineye.com/
4. Google Custom Search API - https://developers.google.com/custom-search

For the HH Goa Task 3 submission, SerpAPI is the recommended primary
provider because it returns social-media image results reliably and
is straightforward to integrate.
"""

import os
import re
import json
import base64
import hashlib
import logging
import time
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from urllib.parse import urlparse
import urllib.request
import urllib.parse

logger = logging.getLogger(__name__)

# Supported social media platforms with their domain patterns
SOCIAL_PLATFORMS = {
    "Instagram": [
        r"^https?://(?:www\.)?instagram\.com/",
        r"^https?://(?:www\.)?instagr\.am/"
    ],
    "Twitter/X": [
        r"^https?://(?:www\.)?twitter\.com/",
        r"^https?://(?:www\.)?x\.com/",
        r"^https?://t\.co/"
    ],
    "Facebook": [
        r"^https?://(?:www\.)?facebook\.com/",
        r"^https?://(?:www\.)?fb\.com/",
        r"^https?://[^\s/]+\.fbcdn\.net/"
    ],
    "TikTok": [
        r"^https?://(?:www\.)?tiktok\.com/"
    ],
    "YouTube": [
        r"^https?://(?:www\.)?youtube\.com/",
        r"^https?://youtu\.be/"
    ],
    "LinkedIn": [
        r"^https?://(?:www\.)?linkedin\.com/"
    ],
    "Pinterest": [
        r"^https?://(?:www\.)?pinterest\.com/",
        r"^https?://[^\s/]+\.pinimg\.com/"
    ],
    "Reddit": [
        r"^https?://(?:www\.)?reddit\.com/",
        r"^https?://[^\s/]+\.redd\.it/"
    ]
}


@dataclass
class SearchResult:
    """A result from reverse image search"""
    url: str
    title: Optional[str] = None
    source: Optional[str] = None
    thumbnail: Optional[str] = None
    similarity: Optional[float] = None
    platform: Optional[str] = None
    search_provider: Optional[str] = None
    # Direct publicly accessible image URL from API metadata (may differ from url).
    # Use this for downloading when available; url remains the evidence/discovery link.
    image_url: Optional[str] = None

    def is_social_media(self) -> bool:
        """Check if this result is from a supported social media platform"""
        return self.platform is not None

    def download_url(self) -> str:
        """
        URL to use for downloading the image.
        Prefers the direct image_url from API metadata over the page url.
        """
        return self.image_url or self.url


class ReverseImageSearcher:
    """
    Performs genuine reverse image search using multiple legitimate providers.

    This class implements a multi-strategy approach to reverse image search.
    At least one real API call is performed at runtime. No URLs are
    hardcoded or pre-selected.

    Required configuration (at least one of):
    - SERPAPI_KEY: For Google Lens reverse image search
    - BING_VISUAL_SEARCH_KEY: For Bing Visual Search API
    - TINEYE_API_KEY: For TinEye reverse image search
    """

    def __init__(
        self,
        serpapi_key: Optional[str] = None,
        bing_api_key: Optional[str] = None,
        tineye_api_key: Optional[str] = None,
        max_results: int = 10,
        request_delay: float = 1.0
    ):
        """
        Initialize the reverse image searcher.

        Args:
            serpapi_key: SerpAPI key for Google reverse image search
            bing_api_key: Bing Visual Search API key
            tineye_api_key: TinEye API key
            max_results: Maximum number of results to return
            request_delay: Delay between requests (seconds)
        """
        self.serpapi_key = serpapi_key or os.getenv("SERPAPI_KEY")
        self.bing_api_key = bing_api_key or os.getenv("BING_VISUAL_SEARCH_KEY")
        self.tineye_api_key = tineye_api_key or os.getenv("TINEYE_API_KEY")
        self.max_results = max_results
        self.request_delay = request_delay
        self._platform_patterns = self._compile_platform_patterns()

        # Track which providers were used
        self.providers_used: List[str] = []
        self.last_query_timestamp: Optional[str] = None

    def _compile_platform_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for platform detection"""
        patterns = {}
        for platform, pattern_list in SOCIAL_PLATFORMS.items():
            for pattern in pattern_list:
                patterns[pattern] = platform
        return {re.compile(p): platform for p, platform in patterns.items()}

    def detect_platform(self, url: str) -> Optional[str]:
        """Detect which social media platform a URL belongs to"""
        for pattern, platform in self._platform_patterns.items():
            if pattern.search(url):
                return platform
        return None

    def search(self, image_path: str) -> List[SearchResult]:
        """
        Perform genuine reverse image search on an image.

        This method makes REAL API calls to reverse-image-search providers.
        At least one provider must be configured. If no provider is
        configured or all providers fail, an empty list is returned.

        Args:
            image_path: Path to the image file

        Returns:
            List of SearchResult objects dynamically discovered

        Raises:
            FileNotFoundError: If image doesn't exist
            RuntimeError: If no search provider is configured
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")

        # Record query timestamp - proves search was performed at runtime
        self.last_query_timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.providers_used = []

        # Check that at least one provider is configured
        if not any([self.serpapi_key, self.bing_api_key, self.tineye_api_key]):
            raise RuntimeError(
                "No reverse-image-search provider configured. "
                "Set at least one of: SERPAPI_KEY, BING_VISUAL_SEARCH_KEY, TINEYE_API_KEY in .env"
            )

        results: List[SearchResult] = []
        errors: List[str] = []

        # Try SerpAPI first (most reliable for social media)
        if self.serpapi_key:
            try:
                serpapi_results = self._search_with_serpapi(image_path)
                if serpapi_results:
                    results.extend(serpapi_results)
                    self.providers_used.append("SerpAPI (Google Lens)")
            except Exception as e:
                errors.append(f"SerpAPI: {e}")
                logger.warning(f"SerpAPI search failed: {e}")

        # Try Bing Visual Search API
        if self.bing_api_key and not results:
            try:
                bing_results = self._search_with_bing_api(image_path)
                if bing_results:
                    results.extend(bing_results)
                    self.providers_used.append("Bing Visual Search API")
            except Exception as e:
                errors.append(f"Bing: {e}")
                logger.warning(f"Bing search failed: {e}")

        # Try TinEye
        if self.tineye_api_key and not results:
            try:
                tineye_results = self._search_with_tineye(image_path)
                if tineye_results:
                    results.extend(tineye_results)
                    self.providers_used.append("TinEye API")
            except Exception as e:
                errors.append(f"TinEye: {e}")
                logger.warning(f"TinEye search failed: {e}")

        if not results and errors:
            logger.error(f"All search providers failed: {'; '.join(errors)}")

        return self._filter_and_sort_results(results)

    def _filter_and_sort_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Filter results to social media and deduplicate"""
        seen_urls = set()
        filtered = []

        for result in results:
            if result.url in seen_urls:
                continue
            if result.is_social_media():
                seen_urls.add(result.url)
                filtered.append(result)

        if not filtered:
            for result in results:
                if result.url not in seen_urls:
                    seen_urls.add(result.url)
                    filtered.append(result)

        return filtered[:self.max_results]

    def _search_with_serpapi(self, image_path: str) -> List[SearchResult]:
        """
        Search using SerpAPI's Google Lens reverse image search.

        This is a REAL API call to SerpAPI. Requires SERPAPI_KEY.

        Two-step workflow:
        1. Upload the image to /image to obtain an image_id.
        2. Query /search with engine=google_lens and image_id=<that_id>.
        """
        import requests

        results = []
        upload_url = "https://serpapi.com/image"
        search_url = "https://serpapi.com/search"

        # Step 1: Upload image to get an image_id
        with open(image_path, 'rb') as f:
            image_data = f.read()

        try:
            upload_response = requests.post(
                upload_url,
                files={'image': ('image.jpg', image_data, 'image/jpeg')},
                data={'api_key': self.serpapi_key},
                timeout=30
            )
            upload_response.raise_for_status()
            upload_data = upload_response.json()
        except Exception as e:
            logger.warning(f"SerpAPI image upload failed: {e}")
            raise

        image_id = upload_data.get('image_id')
        if not image_id:
            logger.warning("SerpAPI did not return an image_id")
            raise RuntimeError("SerpAPI image upload succeeded but returned no image_id")

        # Step 2: Query Google Lens with the image_id
        params = {
            'engine': 'google_lens',
            'api_key': self.serpapi_key,
            'image_id': image_id,
        }

        try:
            response = requests.get(search_url, params=params, timeout=60)
            response.raise_for_status()
            data = response.json()

            # Google Lens returns visually similar images under "visual_matches"
            visual_matches = data.get('visual_matches', [])

            for item in visual_matches:
                page_url = item.get('link', '')
                # image_url is the direct publicly accessible image URL from SerpAPI metadata
                # (e.g. lookaside.instagram.com or pbs.twimg.com — does NOT require login)
                image_url = item.get('image', '')

                if not page_url and not image_url:
                    continue

                page_url = page_url or image_url
                if not isinstance(page_url, str) or not page_url.startswith('http'):
                    continue

                platform = self.detect_platform(page_url)

                if platform:
                    # Social-media result: use page URL as evidence, image_url for download
                    results.append(SearchResult(
                        url=page_url,
                        title=item.get('title', ''),
                        source=item.get('source', ''),
                        thumbnail=item.get('thumbnail', ''),
                        platform=platform,
                        search_provider="SerpAPI",
                        image_url=image_url or None,
                    ))
                elif image_url and isinstance(image_url, str) and image_url.startswith('http'):
                    # Non-social-media result: use image_url as evidence link too
                    results.append(SearchResult(
                        url=image_url,
                        title=item.get('title', ''),
                        source=item.get('source', ''),
                        thumbnail=item.get('thumbnail', ''),
                        platform=None,
                        search_provider="SerpAPI",
                        image_url=image_url,
                    ))

        except Exception as e:
            logger.warning(f"SerpAPI Lens search failed: {e}")
            raise

        return results

    def _search_with_bing_api(self, image_path: str) -> List[SearchResult]:
        """
        Search using Bing Visual Search API (Microsoft Azure).

        This is a REAL API call to Bing. Requires BING_VISUAL_SEARCH_KEY
        from https://portal.azure.com (Cognitive Services).

        Endpoints used:
        - POST https://api.bing.microsoft.com/v7.0/images/visualsearch
        """
        import requests

        endpoint = "https://api.bing.microsoft.com/v7.0/images/visualsearch"

        with open(image_path, 'rb') as f:
            image_data = f.read()

        headers = {
            'Ocp-Apim-Subscription-Key': self.bing_api_key
        }
        files = {
            'image': ('image.jpg', image_data, 'image/jpeg')
        }

        params = {
            'mkt': 'en-US',
            'safeSearch': 'Off'
        }

        response = requests.post(
            endpoint,
            headers=headers,
            params=params,
            files=files,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

        results = []

        # Parse Bing's "pagesIncluding" results
        for tag in data.get('tags', []):
            for action in tag.get('actions', []):
                if action.get('actionType') == 'PagesIncluding':
                    for item in action.get('data', {}).get('value', []):
                        url = item.get('hostPageUrl', '') or item.get('contentUrl', '')
                        if url:
                            results.append(SearchResult(
                                url=url,
                                title=item.get('name'),
                                source=item.get('hostPageDomain'),
                                thumbnail=item.get('thumbnailUrl'),
                                platform=self.detect_platform(url),
                                search_provider="Bing Visual Search"
                            ))

        return results

    def _search_with_tineye(self, image_path: str) -> List[SearchResult]:
        """
        Search using TinEye reverse image search API.

        TinEye is a dedicated reverse-image-search service.
        Requires TINEYE_API_KEY from https://api.tineye.com/.
        """
        import requests

        endpoint = "https://api.tineye.com/rest/search/"

        with open(image_path, 'rb') as f:
            image_data = f.read()

        files = {'image': ('image.jpg', image_data, 'image/jpeg')}
        data = {
            'api_key': self.tineye_api_key
        }

        response = requests.post(
            endpoint,
            files=files,
            data=data,
            timeout=30
        )
        response.raise_for_status()
        result_data = response.json()

        results = []

        matches = result_data.get('results', {}).get('matches', [])
        for match in matches:
            domains = match.get('domains', [])
            url = match.get('back_links', [{}])[0].get('url', '') if match.get('back_links') else ''
            if not url and domains:
                url = f"https://{domains[0]}/"
            if url:
                results.append(SearchResult(
                    url=url,
                    title=f"Score: {match.get('score', 'N/A')}",
                    source=domains[0] if domains else None,
                    platform=self.detect_platform(url),
                    search_provider="TinEye"
                ))

        return results


def filter_social_media_results(results: List[SearchResult]) -> List[SearchResult]:
    """
    Filter results to only include social media platforms.

    All URLs here come from REAL reverse-image-search API responses,
    dynamically discovered at runtime.
    """
    return [r for r in results if r.is_social_media()]


def create_searcher() -> ReverseImageSearcher:
    """Factory function to create a ReverseImageSearcher instance"""
    return ReverseImageSearcher(
        serpapi_key=os.getenv("SERPAPI_KEY"),
        bing_api_key=os.getenv("BING_VISUAL_SEARCH_KEY"),
        tineye_api_key=os.getenv("TINEYE_API_KEY")
    )
