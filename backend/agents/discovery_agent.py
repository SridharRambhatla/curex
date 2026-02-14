import os
import json
import logging
from typing import Dict, Any, List
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from logging_system import AgentLogger, get_log_writer, get_log_config

# Load environment variables
load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent Logger with global log writer
_agent_logger = AgentLogger("discovery_agent", log_writer=get_log_writer(), config=get_log_config())

# --- 1. SYSTEM PROMPT ---
DISCOVERY_SYSTEM_PROMPT = """You are the Discovery Agent for Sidequest, a plot-first experience discovery platform.

Your role is to find compelling, unique experiences based on the user's query and preferences.

Given the user's input, discover and return 5-10 relevant experiences. Focus on:
1. Hyperlocal gems not easily found on Google Maps (look for specific artisan names, hidden cafes, specific workshops).
2. Artisan workshops, heritage walks, cultural immersions.
3. Solo-friendly activities with social scaffolding potential.
4. Experiences with story potential (lore, provenance, friction).

For each experience, provide:
- name: Experience name
- category: One of [food, craft, heritage, nature, art, music, fitness, shopping, networking]
- timing: Best time to visit (e.g., "Saturday 7 AM for fresh flowers")
- budget: Estimated cost in INR (Integer only)
- location: Neighborhood/area in the city
- solo_friendly: Boolean (true/false)
- source: Where you found this (instagram, blog, local_knowledge, etc.)
- description: 2-3 sentence vivid description emphasizing the "vibe" and sensory details.

Return your response as a JSON object with key "discovered_experiences" containing an array of experiences.
Respond ONLY with valid JSON."""

# --- 2. API CONFIGURATION ---
# Assuming you have GOOGLE_API_KEY in your environment variables
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

# Configuration for the model
generation_config = {
    "temperature": 0.4, # Keep it somewhat creative but grounded
    "top_p": 0.95,
    "top_k": 40,
    "max_output_tokens": 8192,
    "response_mime_type": "application/json", # FORCE JSON OUTPUT
}

# Safety settings (Permissive for travel content)
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
}

# --- 3. AGENT FUNCTION ---
@_agent_logger.log_execution
def run_discovery_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Executes the Discovery Agent.
    
    Args:
        state (dict): The current state of the LangGraph/Workflow.
                      Expected keys: 'user_query', 'city', 'budget_range', 'interest_pods'
    
    Returns:
        dict: Updated state with 'discovered_experiences'
    """
    
    user_query = state.get("user_query", "")
    city = state.get("city", "Bangalore") # Default to Bangalore as per MVP
    budget_range = state.get("budget_range", "500-2000")
    interest_pods = state.get("interest_pods", [])
    
    logger.info("="*60)
    logger.info("🔍 DISCOVERY AGENT STARTED")
    logger.info(f"Query: {user_query}")
    logger.info(f"City: {city}")
    logger.info(f"Budget Range: ₹{budget_range}")
    logger.info(f"Interest Pods: {interest_pods}")
    logger.info("="*60)

    # Initialize Model - Using Gemini 2.0 Flash for Speed/Cost efficiency
    model = genai.GenerativeModel(
        model_name="models/gemini-2.0-flash",
        system_instruction=DISCOVERY_SYSTEM_PROMPT,
    )

    # Construct the User Prompt
    # We inject the specific variables into the prompt context
    interest_context = ""
    if interest_pods:
        # Map interest pod IDs to readable categories
        pod_mapping = {
            "food_nerd": "food and drinks",
            "craft_explorer": "crafts and workshops",
            "heritage_walker": "heritage and history",
            "nature_lover": "nature and outdoors",
            "art_enthusiast": "art and galleries",
            "music_lover": "music and performances",
            "fitness_buff": "fitness and wellness",
            "shopping_explorer": "shopping and markets",
            "networking_pro": "networking and community events"
        }
        readable_interests = [pod_mapping.get(pod, pod) for pod in interest_pods]
        interest_context = f"\nUser's Interest Categories: {', '.join(readable_interests)}\nIMPORTANT: Prioritize experiences that match these interest categories. All experiences should be relevant to at least one of these interests."
    
    user_prompt = f"""
    User Request: {user_query}
    Target City: {city}
    Budget Range: ₹{budget_range}{interest_context}
    
    Find specific, actionable experiences that fit the 'Sidequest' vibe (Plot-first, meaningful, local).
    """

    try:
        logger.info("📡 Calling Gemini API...")
        
        # Generate content
        response = model.generate_content(
            user_prompt,
            generation_config=generation_config,
            safety_settings=safety_settings
        )

        logger.info("✅ API Response received")
        logger.info(f"Response length: {len(response.text)} characters")
        
        # Parse JSON output
        # Since we used response_mime_type="application/json", response.text should be pure JSON
        result_json = json.loads(response.text)
        
        # Add metadata for debugging/demo
        result_json['search_metadata'] = {
            "agent": "Discovery Agent",
            "model": "gemini-2.0-flash",
            "city": city
        }
        
        experiences_count = len(result_json.get('discovered_experiences', []))
        logger.info(f"✨ Discovery Agent found {experiences_count} experiences")
        
        # Log each experience name for verification
        for idx, exp in enumerate(result_json.get('discovered_experiences', []), 1):
            logger.info(f"  {idx}. {exp.get('name', 'Unnamed')} - {exp.get('category', 'N/A')}")
        
        logger.info("="*60)
        
        return result_json

    except json.JSONDecodeError as e:
        logger.error("="*60)
        logger.error("❌ JSON PARSING ERROR")
        logger.error(f"Error: {e}")
        logger.error(f"Response text: {response.text[:500]}...")
        logger.error("="*60)
        return {
            "discovered_experiences": [], 
            "error": "Failed to parse agent output"
        }
    except Exception as e:
        logger.error("="*60)
        logger.error("❌ API CALL ERROR")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error("="*60)
        return {
            "discovered_experiences": [], 
            "error": str(e)
        }

# Alias for backward compatibility
run_discovery = run_discovery_agent

# --- 4. EXAMPLE USAGE (For testing) ---
if __name__ == "__main__":
    # Simulate a user state coming from the Supervisor
    test_state = {
        "user_query": "I want a solo date idea involving art or crafts, maybe something messy like pottery.",
        "city": "Bangalore",
        "budget_range": "1000-2500"
    }
    
    result = run_discovery_agent(test_state)
    print(json.dumps(result, indent=2))