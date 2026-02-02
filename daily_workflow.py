import os
import sys
import json
import logging
import requests
import tempfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
import dspy
from fetch_github_commits import fetch_commits_from_last_24_hours, format_commits_for_analysis
from linkedin_post import _get_author_urn

load_dotenv()

# Configure logging
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

log_file = LOG_DIR / f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

# Create handlers
file_handler = logging.FileHandler(log_file, encoding='utf-8')

# Create a safe console handler that handles Windows encoding issues
class SafeConsoleHandler(logging.StreamHandler):
    """Console handler that safely handles emoji/Unicode on Windows."""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Replace emojis with text equivalents for Windows console
            if sys.platform == 'win32':
                emoji_map = {
                    '🚀': '[START]',
                    '📥': '[FETCH]',
                    '📝': '[FORMAT]',
                    '🤖': '[AI]',
                    '🎨': '[IMAGE]',
                    '📤': '[POST]',
                    '✅': '[SUCCESS]',
                    '❌': '[ERROR]',
                    '⚠️': '[WARNING]',
                    'ℹ️': '[INFO]',
                    '✓': '[OK]',
                    '📊': '[METRICS]',
                }
                for emoji, replacement in emoji_map.items():
                    msg = msg.replace(emoji, replacement)
            stream.write(msg + self.terminator)
            self.flush()
        except UnicodeEncodeError:
            # Fallback: remove all non-ASCII characters
            try:
                msg = record.getMessage().encode('ascii', 'replace').decode('ascii')
                stream.write(f"{record.levelname}: {msg}\n")
            except:
                pass

console_handler = SafeConsoleHandler(sys.stdout)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[file_handler, console_handler]
)

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.environ.get("Groq_Api_Key", "")
GEMINI_API_KEY = os.environ.get("Gemini_Api_Key", "")
ACCESS_TOKEN = os.environ.get("access_token", "")
PERSON_URN = os.environ.get("PERSON_URN", "").strip()
BASE_URL = "https://api.linkedin.com/v2"

# DSPy configuration
DSPY_EXAMPLES_FILE = Path("dspy_examples.json")
DSPY_METRICS_FILE = Path("dspy_metrics.json")


class LinkedInPostGenerator(dspy.Signature):
    """Generate an engaging LinkedIn post from GitHub commit activity."""
    
    commits_summary = dspy.InputField(desc="Detailed summary of GitHub commits from last 24 hours")
    post = dspy.OutputField(desc="Engaging LinkedIn post (200-300 words, professional yet friendly tone, with emojis used sparingly, includes call-to-action)")


def setup_dspy():
    """Initialize DSPy with Groq backend."""
    logger.info("Setting up DSPy with Groq backend...")
    
    if not GROQ_API_KEY:
        raise ValueError("Groq_Api_Key not set in .env")
    
    try:
        # Configure DSPy to use Groq via LiteLLM
        # Use groq/ prefix for LiteLLM to recognize Groq provider
        lm = dspy.LM(
            model="groq/llama-3.3-70b-versatile",
            api_key=GROQ_API_KEY
        )
        
        dspy.configure(lm=lm)
        logger.info("[OK] DSPy configured with Groq backend (llama-3.3-70b-versatile)")
        return lm
    except Exception as e:
        logger.error(f"Error setting up DSPy: {e}", exc_info=True)
        raise


def load_dspy_examples():
    """Load past examples for DSPy learning."""
    if DSPY_EXAMPLES_FILE.exists():
        try:
            with open(DSPY_EXAMPLES_FILE, 'r') as f:
                examples = json.load(f)
            logger.info(f"Loaded {len(examples)} DSPy examples from {DSPY_EXAMPLES_FILE}")
            return examples
        except Exception as e:
            logger.warning(f"Error loading DSPy examples: {e}")
            return []
    return []


def save_dspy_example(commits_summary, generated_post, metrics=None):
    """Save a new example for DSPy learning."""
    example = {
        "timestamp": datetime.now().isoformat(),
        "commits_summary": commits_summary[:1000],  # Truncate for storage
        "generated_post": generated_post,
        "metrics": metrics or {}
    }
    
    examples = load_dspy_examples()
    examples.append(example)
    
    # Keep only last 50 examples to avoid file bloat
    if len(examples) > 50:
        examples = examples[-50:]
    
    try:
        with open(DSPY_EXAMPLES_FILE, 'w') as f:
            json.dump(examples, f, indent=2)
        logger.info(f"Saved new DSPy example (total: {len(examples)})")
    except Exception as e:
        logger.error(f"Error saving DSPy example: {e}")


def analyze_commits_with_dspy(commits_summary):
    """Use DSPy to analyze commits and create a beautiful LinkedIn post."""
    logger.info("Starting DSPy analysis of commits...")
    
    try:
        # Setup DSPy
        setup_dspy()
        
        # Create DSPy module
        generate_post = dspy.ChainOfThought(LinkedInPostGenerator)
        
        # Load past examples for context (optional, for future optimization)
        examples = load_dspy_examples()
        if examples:
            logger.info(f"Using {len(examples)} past examples for context")
        
        # Generate post
        logger.info("Generating LinkedIn post with DSPy...")
        result = generate_post(commits_summary=commits_summary)
        
        post_text = result.post.strip()
        
        # Log metrics
        metrics = {
            "input_length": len(commits_summary),
            "output_length": len(post_text),
            "word_count": len(post_text.split()),
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info(f"✓ Post generated successfully (length: {len(post_text)} chars, {metrics['word_count']} words)")
        
        # Save example for learning
        save_dspy_example(commits_summary, post_text, metrics)
        
        return post_text
        
    except Exception as e:
        logger.error(f"Error with DSPy analysis: {e}", exc_info=True)
        raise


def generate_image_with_gemini(post_text):
    """Use Gemini Imagen API to generate an image based on the LinkedIn post."""
    logger.info("Starting Gemini Imagen image generation...")
    
    if not GEMINI_API_KEY:
        raise ValueError("Gemini_Api_Key not set in .env")
    
    # Create a prompt for image generation based on the post
    image_prompt = f"""Professional, modern LinkedIn post image about software development and coding.

Visual style: Clean, modern, tech-focused design with professional color scheme. 
Theme: Coding, GitHub commits, software development, programming.
Mood: Professional, engaging, inspiring for developers.
Design elements: Code snippets, GitHub logo, developer tools, clean typography.
Color palette: Professional blues, greens, or modern gradients.
Avoid: Cluttered designs, unprofessional imagery.

The post content is about: {post_text[:300]}"""

    try:
        logger.info("Calling Gemini Imagen API...")
        # Use Gemini's Imagen API for image generation
        # Correct endpoint format: imagen-4.0-generate-001:predict
        imagen_url = "https://generativelanguage.googleapis.com/v1beta/models/imagen-4.0-generate-001:predict"
        
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        }
        
        # Correct payload format for Imagen API
        payload = {
            "instances": [
                {
                    "prompt": image_prompt
                }
            ],
            "parameters": {
                "sampleCount": 1,
                "aspectRatio": "1:1",  # Square for LinkedIn
                "safetyFilterLevel": "block_some",
                "personGeneration": "allow_all"
            }
        }
        
        logger.debug(f"Imagen API URL: {imagen_url}")
        logger.debug(f"Payload keys: {list(payload.keys())}")
        
        response = requests.post(imagen_url, headers=headers, json=payload)
        logger.info(f"Gemini API response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info("Gemini API response received successfully")
            logger.debug(f"Response keys: {list(result.keys())}")
            
            # Imagen API returns predictions array
            if "predictions" in result and len(result["predictions"]) > 0:
                prediction = result["predictions"][0]
                logger.info("Image prediction extracted from response")
                logger.debug(f"Prediction keys: {list(prediction.keys())}")
                
                # Check for base64 encoded image
                if "bytesBase64Encoded" in prediction:
                    logger.info("Using base64 encoded image from prediction")
                    return f"data:image/png;base64,{prediction['bytesBase64Encoded']}"
                elif "mimeType" in prediction and "bytesBase64Encoded" in prediction:
                    mime_type = prediction.get("mimeType", "image/png")
                    logger.info(f"Using base64 encoded image (mime: {mime_type})")
                    return f"data:{mime_type};base64,{prediction['bytesBase64Encoded']}"
                else:
                    logger.warning("Unexpected Imagen response format - no bytesBase64Encoded found")
                    logger.debug(f"Prediction structure: {prediction}")
                    return None
            else:
                logger.warning("No predictions in Gemini response")
                logger.debug(f"Response structure: {result}")
                return None
        elif response.status_code == 400:
            error_data = response.json()
            error_msg = error_data.get("error", {}).get("message", "")
            
            if "billed users" in error_msg.lower() or "billing" in error_msg.lower():
                logger.warning("Imagen API requires a paid Google Cloud account with billing enabled")
                logger.info("Skipping image generation - Imagen API is not available for free tier")
                logger.info("Tip: Enable billing in Google Cloud Console to use Imagen API")
                return None
            else:
                logger.error(f"Gemini Imagen API error: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None
        else:
            logger.error(f"Gemini Imagen API error: {response.status_code}")
            logger.error(f"Response: {response.text}")
            return None
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error with Gemini API: {e}", exc_info=True)
        return None
    except Exception as e:
        logger.error(f"Unexpected error with Gemini Imagen API: {e}", exc_info=True)
        return None


def upload_image_to_linkedin(image_url_or_data):
    """Upload an image to LinkedIn and get the media URN."""
    logger.info("Starting LinkedIn image upload process...")
    
    if not ACCESS_TOKEN:
        raise ValueError("access_token not set in .env")
    
    try:
        author_urn = _get_author_urn()
        logger.info(f"Got author URN: {author_urn}")
        
        # Step 1: Register upload
        logger.info("Registering image upload with LinkedIn...")
        register_url = f"{BASE_URL}/assets?action=registerUpload"
        register_payload = {
            "registerUploadRequest": {
                "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
                "owner": author_urn,
                "serviceRelationships": [
                    {
                        "relationshipType": "OWNER",
                        "identifier": "urn:li:userGeneratedContent"
                    }
                ]
            }
        }
        
        resp = requests.post(
            register_url,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=register_payload,
        )
        resp.raise_for_status()
        register_data = resp.json()
        logger.info("✓ Image upload registered successfully")
        
        upload_url = register_data["value"]["uploadMechanism"]["com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest"]["uploadUrl"]
        asset_urn = register_data["value"]["asset"]
        logger.info(f"Got upload URL and asset URN: {asset_urn}")
        
        # Step 2: Get image data
        logger.info("Preparing image data for upload...")
        if image_url_or_data.startswith("http"):
            logger.info("Downloading image from URL...")
            img_resp = requests.get(image_url_or_data)
            img_resp.raise_for_status()
            img_data = img_resp.content
            logger.info(f"Downloaded image ({len(img_data)} bytes)")
        elif image_url_or_data.startswith("data:image"):
            logger.info("Decoding base64 image data...")
            import base64
            header, encoded = image_url_or_data.split(",", 1)
            img_data = base64.b64decode(encoded)
            logger.info(f"Decoded image ({len(img_data)} bytes)")
        else:
            logger.info("Decoding base64 string...")
            import base64
            img_data = base64.b64decode(image_url_or_data)
            logger.info(f"Decoded image ({len(img_data)} bytes)")
        
        # Step 3: Upload image
        logger.info("Uploading image to LinkedIn...")
        upload_resp = requests.post(
            upload_url,
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
            },
            data=img_data,
        )
        upload_resp.raise_for_status()
        logger.info("✓ Image uploaded successfully")
        
        return asset_urn
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during LinkedIn image upload: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error uploading image to LinkedIn: {e}", exc_info=True)
        raise


def post_to_linkedin_with_image(post_text, image_urn=None):
    """Post to LinkedIn with optional image."""
    logger.info("Preparing LinkedIn post...")
    
    if not ACCESS_TOKEN:
        raise ValueError("access_token not set in .env")
    
    try:
        author_urn = _get_author_urn()
        logger.info(f"Using author URN: {author_urn}")
        
        payload = {
            "author": author_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": post_text},
                    "shareMediaCategory": "IMAGE" if image_urn else "NONE",
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
        }
        
        if image_urn:
            logger.info("Adding image to post payload")
            payload["specificContent"]["com.linkedin.ugc.ShareContent"]["media"] = [
                {
                    "status": "READY",
                    "media": image_urn,
                }
            ]
        else:
            logger.info("Posting text-only (no image)")
        
        logger.info("Sending post to LinkedIn API...")
        resp = requests.post(
            f"{BASE_URL}/ugcPosts",
            headers={
                "Authorization": f"Bearer {ACCESS_TOKEN}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0",
            },
            json=payload,
        )
        
        logger.info(f"LinkedIn API response status: {resp.status_code}")
        
        if resp.status_code != 201:
            logger.error(f"LinkedIn API error: {resp.status_code}")
            logger.error(f"Response: {resp.text}")
        
        resp.raise_for_status()
        result = resp.json()
        logger.info("✓ Post created successfully")
        
        return result
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error posting to LinkedIn: {e}", exc_info=True)
        raise
    except Exception as e:
        logger.error(f"Error posting to LinkedIn: {e}", exc_info=True)
        raise


def run_daily_workflow():
    """Main workflow: Fetch commits, analyze, generate image, post to LinkedIn."""
    logger.info("=" * 80)
    logger.info("🚀 Starting Daily GitHub Commit Workflow")
    logger.info("=" * 80)
    logger.info(f"Log file: {log_file}")
    
    workflow_start_time = datetime.now()
    
    try:
        # Step 1: Fetch GitHub commits from last 24 hours
        logger.info("\n" + "=" * 80)
        logger.info("📥 Step 1: Fetching GitHub commits from last 24 hours...")
        logger.info("=" * 80)
        
        try:
            commits = fetch_commits_from_last_24_hours()
            logger.info(f"✓ Fetched commits: {len(commits)} commit(s) found")
            
            if not commits:
                logger.info("ℹ️  No commits found in the last 24 hours. Skipping post.")
                return
            
            for i, commit in enumerate(commits, 1):
                logger.info(f"  Commit {i}: {commit['repository']} - {commit['message'][:50]}...")
                
        except Exception as e:
            logger.error(f"❌ Error fetching GitHub commits: {e}", exc_info=True)
            raise
        
        # Step 2: Format commits for analysis
        logger.info("\n" + "=" * 80)
        logger.info("📝 Step 2: Formatting commits for analysis...")
        logger.info("=" * 80)
        
        try:
            commits_summary = format_commits_for_analysis(commits)
            logger.info(f"✓ Formatted {len(commits)} commit(s)")
            logger.debug(f"Summary length: {len(commits_summary)} characters")
        except Exception as e:
            logger.error(f"❌ Error formatting commits: {e}", exc_info=True)
            raise
        
        # Step 3: Analyze with DSPy and create LinkedIn post
        logger.info("\n" + "=" * 80)
        logger.info("🤖 Step 3: Analyzing commits with DSPy AI...")
        logger.info("=" * 80)
        
        try:
            post_text = analyze_commits_with_dspy(commits_summary)
            logger.info("✓ LinkedIn post generated")
            logger.info(f"\n📄 Generated Post:\n{post_text}\n")
        except Exception as e:
            logger.error(f"❌ Error generating post with DSPy: {e}", exc_info=True)
            raise
        
        # Step 4: Generate image with Gemini
        logger.info("\n" + "=" * 80)
        logger.info("🎨 Step 4: Generating image with Gemini Imagen...")
        logger.info("=" * 80)
        
        image_urn = None
        image_url = None
        
        try:
            image_url = generate_image_with_gemini(post_text)
            if image_url:
                logger.info("✓ Image generated successfully")
                
                # Download and upload to LinkedIn
                logger.info("📤 Uploading image to LinkedIn...")
                try:
                    image_urn = upload_image_to_linkedin(image_url)
                    logger.info(f"✓ Image uploaded, URN: {image_urn}")
                except Exception as e:
                    logger.warning(f"⚠️  Image upload failed: {e}")
                    logger.info("ℹ️  Continuing with text-only post")
                    image_urn = None
            else:
                logger.info("ℹ️  No image generated, posting text-only")
        except Exception as e:
            logger.warning(f"⚠️  Image generation/upload skipped: {e}")
            logger.info("ℹ️  Continuing with text-only post")
        
        # Step 5: Post to LinkedIn
        logger.info("\n" + "=" * 80)
        logger.info("📤 Step 5: Posting to LinkedIn...")
        logger.info("=" * 80)
        
        try:
            result = post_to_linkedin_with_image(post_text, image_urn)
            logger.info("✓ Successfully posted to LinkedIn!")
            logger.info(f"Post ID: {result.get('id', 'N/A')}")
            
            # Log success metrics
            workflow_duration = (datetime.now() - workflow_start_time).total_seconds()
            logger.info(f"\n📊 Workflow Metrics:")
            logger.info(f"  Duration: {workflow_duration:.2f} seconds")
            logger.info(f"  Commits processed: {len(commits)}")
            logger.info(f"  Post length: {len(post_text)} characters")
            logger.info(f"  Image included: {'Yes' if image_urn else 'No'}")
            
        except Exception as e:
            logger.error(f"❌ Error posting to LinkedIn: {e}", exc_info=True)
            raise
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ Daily workflow completed successfully!")
        logger.info("=" * 80)
        
    except Exception as e:
        workflow_duration = (datetime.now() - workflow_start_time).total_seconds()
        logger.error("\n" + "=" * 80)
        logger.error(f"❌ Error in workflow after {workflow_duration:.2f} seconds: {e}")
        logger.error("=" * 80, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        run_daily_workflow()
    except KeyboardInterrupt:
        logger.warning("Workflow interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
