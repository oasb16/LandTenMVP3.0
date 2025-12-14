"""
GPT-4o Vision Service for Property Issue Detection

This module provides AI-powered image analysis for property maintenance issues
using OpenAI's GPT-4o Vision model. It analyzes photos of property damage and
generates human-readable summaries for property managers and landlords.

Key Features:
- Property issue detection (water damage, cracks, structural issues, etc.)
- Image validation and compression
- Retry logic with exponential backoff
- Cost optimization
- Comprehensive error handling and logging
"""

import base64
import io
import logging
import time
import hashlib
from typing import Optional, Dict, Any, Tuple
from functools import wraps
from PIL import Image
import asyncio

from openai import OpenAI, APIError, RateLimitError, AuthenticationError
from ..config.settings import settings

logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Vision model configuration
VISION_MODEL = "gpt-4o"  # Use gpt-4o for vision capabilities
MAX_TOKENS = 300  # Limit response length for cost optimization
TEMPERATURE = 0.3  # Lower temperature for more focused responses

# Image constraints
MAX_IMAGE_SIZE_BYTES = 20 * 1024 * 1024  # 20MB (OpenAI limit)
MAX_IMAGE_SIZE_KB = 500  # Target size after compression
MIN_IMAGE_DIMENSION = 50  # Minimum width/height in pixels
MAX_IMAGE_DIMENSION = 1024  # Resize larger images to this

# Allowed image formats
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'GIF', 'WEBP'}

# Retry configuration
MAX_RETRIES = 3
BASE_RETRY_DELAY = 2  # seconds
MAX_RETRY_TIME = 30  # seconds total

# Vision analysis prompts
DEFAULT_VISION_PROMPT = """You are a property maintenance expert. Analyze this image carefully and:

1. Identify any visible property issues (water damage, cracks, leaks, mold, structural damage, electrical issues, plumbing issues, etc.)
2. Describe the severity (minor, moderate, severe)
3. Suggest the type of repair needed
4. If no issues are visible, state 'No visible property issues detected.'

Be specific and concise. Focus on actionable information."""

SPECIALIZED_PROMPTS = {
    "water_damage": """Analyze this image specifically for water damage:
- Look for water stains, discoloration, mold, dampness
- Assess severity (minor seepage, moderate damage, severe flooding)
- Identify likely source (roof, plumbing, condensation, foundation)
- Recommend immediate actions""",

    "structural": """Analyze this image for structural issues:
- Cracks in walls, ceilings, or foundations
- Sagging, warping, or bowing
- Deterioration of materials
- Safety concerns and urgency""",

    "electrical": """Analyze this image for electrical hazards:
- Exposed wiring or damaged insulation
- Damaged outlets, switches, or fixtures
- Burn marks or scorching
- Code violations and safety risks""",

    "plumbing": """Analyze this image for plumbing issues:
- Visible leaks or water damage
- Corroded or damaged pipes
- Drainage problems
- Fixture damage or malfunction""",
}

# ============================================================================
# EXCEPTIONS
# ============================================================================

class VisionAnalysisError(Exception):
    """Base exception for vision analysis errors"""
    pass

class ImageValidationError(VisionAnalysisError):
    """Raised when image validation fails"""
    pass

class VisionAPIError(VisionAnalysisError):
    """Raised when OpenAI Vision API call fails"""
    pass


# ============================================================================
# IMAGE VALIDATION & COMPRESSION
# ============================================================================

def validate_image(image_bytes: bytes) -> Tuple[bool, str]:
    """
    Validate image format and size.

    Args:
        image_bytes: Raw image bytes

    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Check if empty
        if not image_bytes or len(image_bytes) == 0:
            return False, "Image data is empty"

        # Check file size (max 20MB for OpenAI)
        if len(image_bytes) > MAX_IMAGE_SIZE_BYTES:
            size_mb = len(image_bytes) / 1024 / 1024
            return False, f"Image too large: {size_mb:.1f}MB (max 20MB)"

        # Validate image format
        try:
            image = Image.open(io.BytesIO(image_bytes))
            image.verify()  # Verify it's a valid image

            # Re-open after verify (verify() closes the file)
            image = Image.open(io.BytesIO(image_bytes))

            if image.format not in ALLOWED_IMAGE_FORMATS:
                return False, f"Unsupported format: {image.format}. Use JPEG, PNG, GIF, or WEBP"

            # Check image dimensions
            width, height = image.size
            if width < MIN_IMAGE_DIMENSION or height < MIN_IMAGE_DIMENSION:
                return False, f"Image too small: {width}x{height}. Minimum {MIN_IMAGE_DIMENSION}x{MIN_IMAGE_DIMENSION} pixels"

            logger.info(
                f"✅ Image validated: {image.format}, {width}x{height}, "
                f"{len(image_bytes)/1024:.1f}KB"
            )

            return True, ""

        except Exception as e:
            return False, f"Invalid image file: {str(e)}"

    except Exception as e:
        logger.error(f"Error validating image: {e}", exc_info=True)
        return False, f"Image validation failed: {str(e)}"


def compress_image(
    image_bytes: bytes,
    max_size_kb: int = MAX_IMAGE_SIZE_KB,
    max_dimension: int = MAX_IMAGE_DIMENSION
) -> bytes:
    """
    Compress image to reduce API costs and improve speed.

    Args:
        image_bytes: Original image bytes
        max_size_kb: Target maximum size in KB
        max_dimension: Maximum width/height (maintains aspect ratio)

    Returns:
        Compressed image bytes
    """
    try:
        img = Image.open(io.BytesIO(image_bytes))
        original_size = len(image_bytes)

        # Convert RGBA/LA/P to RGB if necessary
        if img.mode in ('RGBA', 'LA', 'P'):
            # Create white background
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = background

        # Resize if too large (maintain aspect ratio)
        if max(img.size) > max_dimension:
            ratio = max_dimension / max(img.size)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            img = img.resize(new_size, Image.Resampling.LANCZOS)
            logger.info(f"📐 Resized image to {new_size[0]}x{new_size[1]}")

        # Compress with quality adjustment
        output = io.BytesIO()
        quality = 85

        while quality > 20:
            output.seek(0)
            output.truncate()
            img.save(output, format='JPEG', quality=quality, optimize=True)

            if len(output.getvalue()) / 1024 <= max_size_kb:
                break

            quality -= 5

        compressed_bytes = output.getvalue()
        compression_ratio = (1 - len(compressed_bytes) / original_size) * 100

        logger.info(
            f"🗜️ Compressed image: {original_size/1024:.1f}KB → "
            f"{len(compressed_bytes)/1024:.1f}KB ({compression_ratio:.1f}% reduction, "
            f"quality: {quality})"
        )

        return compressed_bytes

    except Exception as e:
        logger.warning(f"⚠️ Image compression failed, using original: {e}")
        return image_bytes


def get_image_hash(image_bytes: bytes) -> str:
    """Generate unique hash for image (for caching)"""
    return hashlib.sha256(image_bytes).hexdigest()


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry_on_failure(max_retries: int = MAX_RETRIES, delay: int = BASE_RETRY_DELAY):
    """Decorator to retry function on failure with exponential backoff"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)

                except (APIError, RateLimitError) as e:
                    elapsed = time.time() - start_time

                    if attempt == max_retries - 1:
                        # Last attempt failed
                        raise VisionAPIError(
                            f"Vision analysis failed after {max_retries} attempts: {str(e)}"
                        )

                    if elapsed >= MAX_RETRY_TIME:
                        # Exceeded max retry time
                        raise VisionAPIError(
                            f"Vision analysis timeout after {elapsed:.1f}s: {str(e)}"
                        )

                    # Calculate backoff delay
                    wait_time = delay * (2 ** attempt)

                    # Don't wait longer than remaining time
                    remaining_time = MAX_RETRY_TIME - elapsed
                    wait_time = min(wait_time, remaining_time)

                    logger.warning(
                        f"⚠️ Attempt {attempt + 1}/{max_retries} failed. "
                        f"Retrying in {wait_time:.1f}s... Error: {str(e)}"
                    )

                    await asyncio.sleep(wait_time)

            return await func(*args, **kwargs)

        return wrapper
    return decorator


# ============================================================================
# CORE VISION ANALYSIS FUNCTION
# ============================================================================

@retry_on_failure(max_retries=MAX_RETRIES, delay=BASE_RETRY_DELAY)
async def call_gpt_vision(
    image_bytes: bytes,
    custom_prompt: Optional[str] = None,
    issue_type: str = "general",
    compress: bool = True
) -> str:
    """
    Analyze an image using OpenAI GPT-4o Vision to detect property issues.

    Args:
        image_bytes: Raw image bytes (JPEG, PNG, etc.)
        custom_prompt: Custom analysis prompt (overrides issue_type)
        issue_type: Type of analysis ("general", "water_damage", "structural", "electrical", "plumbing")
        compress: Whether to compress image before sending (default: True)

    Returns:
        AI-generated summary of visible property issues

    Raises:
        ImageValidationError: If image is invalid
        VisionAPIError: If API call fails after retries
    """
    start_time = time.time()

    # Validate input
    if not image_bytes or len(image_bytes) == 0:
        raise ImageValidationError("image_bytes cannot be empty")

    # Validate image
    is_valid, error_msg = validate_image(image_bytes)
    if not is_valid:
        raise ImageValidationError(error_msg)

    try:
        # Compress image if requested
        if compress:
            image_bytes = compress_image(image_bytes)

        # Convert image to base64
        base64_image = base64.b64encode(image_bytes).decode("utf-8")
        logger.info(f"🔍 Encoded image to base64 ({len(base64_image)} chars)")

        # Select prompt
        if custom_prompt:
            prompt_text = custom_prompt
        else:
            prompt_text = SPECIALIZED_PROMPTS.get(issue_type, DEFAULT_VISION_PROMPT)

        # Prepare vision API request
        vision_messages = [{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt_text},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"  # Use "high" for detailed analysis
                    }
                }
            ]
        }]

        # Initialize OpenAI client
        openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)

        # Call OpenAI Vision API
        logger.info(f"📞 Calling OpenAI GPT-4o Vision API (issue_type={issue_type})...")

        # Use asyncio.to_thread to make sync call async
        response = await asyncio.to_thread(
            openai_client.chat.completions.create,
            model=VISION_MODEL,
            messages=vision_messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )

        # Extract analysis result
        analysis_result = response.choices[0].message.content

        # Log success
        elapsed = time.time() - start_time
        tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 'N/A'

        logger.info(
            f"✅ Vision analysis complete: {len(analysis_result)} chars, "
            f"{tokens_used} tokens, {elapsed:.2f}s"
        )

        return analysis_result

    except AuthenticationError as e:
        logger.error(f"🔑 OpenAI authentication error: {e}")
        raise VisionAPIError(f"Authentication failed: {str(e)}")

    except RateLimitError as e:
        logger.error(f"⏱️ OpenAI rate limit exceeded: {e}")
        raise  # Let retry decorator handle this

    except APIError as e:
        logger.error(f"❌ OpenAI API error: {e}")
        raise  # Let retry decorator handle this

    except Exception as e:
        logger.error(f"💥 Unexpected error in vision analysis: {e}", exc_info=True)
        raise VisionAPIError(f"Vision analysis failed: {str(e)}")


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

async def analyze_property_image(
    image_bytes: bytes,
    issue_type: str = "general"
) -> Dict[str, Any]:
    """
    Analyze property image with comprehensive error handling.

    Returns a structured result with success status and either the analysis
    result or error information.

    Args:
        image_bytes: Raw image bytes
        issue_type: Type of issue to analyze

    Returns:
        Dict with keys: success, result, error, error_type
    """
    try:
        # Validate image
        is_valid, error_msg = validate_image(image_bytes)
        if not is_valid:
            return {
                "success": False,
                "result": None,
                "error": error_msg,
                "error_type": "validation_error"
            }

        # Analyze image
        result = await call_gpt_vision(image_bytes, issue_type=issue_type)

        return {
            "success": True,
            "result": result,
            "error": None,
            "error_type": None
        }

    except ImageValidationError as e:
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "error_type": "validation_error"
        }

    except VisionAPIError as e:
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "error_type": "api_error"
        }

    except Exception as e:
        logger.exception("Unexpected error in analyze_property_image")
        return {
            "success": False,
            "result": None,
            "error": f"Unexpected error: {str(e)}",
            "error_type": "unknown_error"
        }


# ============================================================================
# SIMPLE CACHE (In-memory)
# ============================================================================

# Simple in-memory cache for duplicate image detection
_vision_cache: Dict[str, str] = {}

async def call_gpt_vision_cached(
    image_bytes: bytes,
    issue_type: str = "general"
) -> str:
    """
    Vision analysis with caching to avoid duplicate API calls for same image.

    Args:
        image_bytes: Raw image bytes
        issue_type: Type of analysis

    Returns:
        Analysis result (from cache or fresh API call)
    """
    # Generate cache key
    image_hash = get_image_hash(image_bytes)
    cache_key = f"{image_hash}:{issue_type}"

    # Check cache
    if cache_key in _vision_cache:
        logger.info(f"💰 Cache hit for image {image_hash[:8]}... (issue_type={issue_type})")
        return _vision_cache[cache_key]

    # Cache miss - call API
    logger.info(f"🔍 Cache miss for image {image_hash[:8]}... (issue_type={issue_type})")
    result = await call_gpt_vision(image_bytes, issue_type=issue_type)

    # Store in cache
    _vision_cache[cache_key] = result

    # Simple cache cleanup: remove oldest entries if cache gets too large
    if len(_vision_cache) > 100:
        # Remove first 20 entries (FIFO)
        keys_to_remove = list(_vision_cache.keys())[:20]
        for key in keys_to_remove:
            del _vision_cache[key]
        logger.info(f"🧹 Cache cleanup: removed {len(keys_to_remove)} entries")

    return result
