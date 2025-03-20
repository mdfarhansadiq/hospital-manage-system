import os
from datetime import datetime, timedelta
import logging
from openai import OpenAI
import time
import json
import redis

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Configure OpenAI client
client = OpenAI(
    api_key=""
)

# Configure Redis client
redis_client = redis.Redis(
    host='localhost',
    port=6379,
    db=0,
    decode_responses=True
)

def get_cache_key(patient_id):
    """Generate a cache key for a patient's wellness tip."""
    return f"wellness_tip:{patient_id}"

def get_cached_tip(patient_id):
    """Retrieve a cached wellness tip if available."""
    try:
        cache_key = get_cache_key(patient_id)
        cached_data = redis_client.get(cache_key)

        if cached_data:
            tip_data = json.loads(cached_data)
            # Convert string timestamp back to datetime
            tip_data['generated_at'] = datetime.fromisoformat(tip_data['generated_at'])
            logger.debug(f"Cache hit for patient {patient_id}")
            return tip_data

        logger.debug(f"Cache miss for patient {patient_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving from cache: {str(e)}")
        return None

def cache_tip(patient_id, tip_data):
    """Cache a wellness tip with 24-hour expiration."""
    try:
        cache_key = get_cache_key(patient_id)
        # Convert datetime to ISO format string for JSON serialization
        tip_data['generated_at'] = tip_data['generated_at'].isoformat()

        redis_client.setex(
            cache_key,
            timedelta(hours=24),
            json.dumps(tip_data)
        )
        logger.debug(f"Successfully cached tip for patient {patient_id}")
    except Exception as e:
        logger.error(f"Error caching tip: {str(e)}")

def generate_wellness_tip(patient):
    """
    Generate a personalized wellness tip based on patient data.
    Implements caching to improve performance.

    Args:
        patient: Patient object containing medical history and current condition

    Returns:
        dict: Contains the generated tip and metadata
    """
    try:
        # Check cache first
        cached_tip = get_cached_tip(patient.id)
        if cached_tip:
            return cached_tip

        # Construct prompt based on patient data
        conditions = ", ".join([h.condition for h in patient.medical_history])
        allergies = ", ".join([a.allergen for a in patient.allergies])

        # Create a context-aware prompt
        prompt = f"""Generate a personalized wellness tip for a patient with the following profile:
        - Age: {patient.age}
        - Gender: {patient.gender}
        - Medical Conditions: {conditions if conditions else 'No known conditions'}
        - Allergies: {allergies if allergies else 'No known allergies'}

        Please provide a specific, actionable wellness tip that:
        1. Is appropriate for their medical conditions
        2. Takes into account any allergies
        3. Is age-appropriate
        4. Focuses on preventive health and well-being
        5. Is concise (maximum 2-3 sentences)

        The tip should be encouraging and positive in tone."""

        max_retries = 3
        retry_delay = 1

        for attempt in range(max_retries):
            try:
                # Call OpenAI API with the new configuration
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a healthcare professional providing personalized wellness advice."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.7
                )

                # Extract the generated tip
                tip = response.choices[0].message.content.strip()

                tip_data = {
                    'tip': tip,
                    'generated_at': datetime.utcnow(),
                    'success': True
                }

                # Cache the successful response
                cache_tip(patient.id, tip_data)

                return tip_data
            except Exception as retry_error:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed: {str(retry_error)}")
                    time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    raise retry_error

    except Exception as e:
        error_data = {
            'tip': "Unable to generate wellness tip at this time. Please try again later.",
            'generated_at': datetime.utcnow(),
            'success': False,
            'error': str(e)
        }
        return error_data
