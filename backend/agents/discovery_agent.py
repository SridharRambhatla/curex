import os
import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta, MO, TU, WE, TH, FR, SA, SU
from dotenv import load_dotenv
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from logging_system import AgentLogger, get_log_writer, get_log_config

# Load environment variables
load_dotenv()

# Import geocoding utility
from utils.geocoding import geocode_experiences


# --- DATE PARSING UTILITY ---
def parse_date_from_query(query: str) -> Tuple[Optional[datetime], Optional[str], Optional[str]]:
    """
    Extract date information from user query.
    
    Returns:
        Tuple of (parsed_date, day_of_week, date_constraint_text)
        - parsed_date: datetime object if a specific date was found
        - day_of_week: 'monday', 'tuesday', etc. or None
        - date_constraint_text: Human-readable constraint to add to prompt
    """
    query_lower = query.lower()
    today = datetime.now()
    
    # Day name mapping
    day_names = {
        'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
        'friday': 4, 'saturday': 5, 'sunday': 6,
        'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3, 'fri': 4, 'sat': 5, 'sun': 6
    }
    
    day_weekday_map = {
        0: MO, 1: TU, 2: WE, 3: TH, 4: FR, 5: SA, 6: SU
    }
    
    parsed_date = None
    day_of_week = None
    constraint = None
    
    # Check for "today"
    if 'today' in query_lower:
        parsed_date = today
        day_of_week = today.strftime('%A').lower()
        constraint = f"User wants experiences for TODAY ({today.strftime('%A, %B %d, %Y')}). ONLY return experiences that are open/available on {day_of_week}s."
        return parsed_date, day_of_week, constraint
    
    # Check for "tomorrow"
    if 'tomorrow' in query_lower:
        parsed_date = today + timedelta(days=1)
        day_of_week = parsed_date.strftime('%A').lower()
        constraint = f"User wants experiences for TOMORROW ({parsed_date.strftime('%A, %B %d, %Y')}). ONLY return experiences that are open/available on {day_of_week}s."
        return parsed_date, day_of_week, constraint
    
    # Check for "day after tomorrow"
    if 'day after tomorrow' in query_lower:
        parsed_date = today + timedelta(days=2)
        day_of_week = parsed_date.strftime('%A').lower()
        constraint = f"User wants experiences for {parsed_date.strftime('%A, %B %d, %Y')}. ONLY return experiences that are open/available on {day_of_week}s."
        return parsed_date, day_of_week, constraint
    
    # Check for "this weekend"
    if 'this weekend' in query_lower:
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0 and today.weekday() == 5:
            parsed_date = today  # Today is Saturday
        else:
            parsed_date = today + timedelta(days=days_until_saturday)
        constraint = f"User wants experiences for THIS WEEKEND (Saturday {parsed_date.strftime('%B %d')} or Sunday {(parsed_date + timedelta(days=1)).strftime('%B %d')}). ONLY return experiences available on Saturday OR Sunday."
        return parsed_date, 'weekend', constraint
    
    # Check for "next weekend"
    if 'next weekend' in query_lower:
        days_until_saturday = (5 - today.weekday()) % 7
        if days_until_saturday == 0:
            days_until_saturday = 7  # Skip to next week's Saturday
        parsed_date = today + timedelta(days=days_until_saturday + 7)
        constraint = f"User wants experiences for NEXT WEEKEND (Saturday {parsed_date.strftime('%B %d')} or Sunday {(parsed_date + timedelta(days=1)).strftime('%B %d')}). ONLY return experiences available on Saturday OR Sunday."
        return parsed_date, 'weekend', constraint
    
    # Check for "this [day]" or "next [day]"
    for day_name, day_num in day_names.items():
        # "this monday", "this saturday", etc.
        if f'this {day_name}' in query_lower:
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                parsed_date = today
            else:
                parsed_date = today + timedelta(days=days_ahead)
            day_of_week = list(day_names.keys())[day_num] if day_num < 7 else day_name
            constraint = f"User wants experiences for THIS {day_of_week.upper()} ({parsed_date.strftime('%B %d, %Y')}). ONLY return experiences that are open/available on {day_of_week}s."
            return parsed_date, day_of_week, constraint
        
        # "next monday", "next saturday", etc.
        if f'next {day_name}' in query_lower:
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # Go to next week
            parsed_date = today + timedelta(days=days_ahead + 7)
            day_of_week = list(day_names.keys())[day_num] if day_num < 7 else day_name
            constraint = f"User wants experiences for NEXT {day_of_week.upper()} ({parsed_date.strftime('%B %d, %Y')}). ONLY return experiences that are open/available on {day_of_week}s."
            return parsed_date, day_of_week, constraint
        
        # Just the day name (e.g., "saturday", "on monday")
        if day_name in query_lower and f'this {day_name}' not in query_lower and f'next {day_name}' not in query_lower:
            # Assume the upcoming occurrence
            days_ahead = (day_num - today.weekday()) % 7
            if days_ahead == 0:
                parsed_date = today  # It's that day today
            else:
                parsed_date = today + timedelta(days=days_ahead)
            day_of_week = list(day_names.keys())[day_num] if day_num < 7 else day_name
            constraint = f"User wants experiences for {day_of_week.upper()} ({parsed_date.strftime('%B %d, %Y')}). ONLY return experiences that are open/available on {day_of_week}s."
            return parsed_date, day_of_week, constraint
    
    # Try to parse specific dates using dateutil
    # Match patterns like "Feb 15", "15th February", "2/15", "February 15th"
    date_patterns = [
        r'\b(\d{1,2})[\/\-](\d{1,2})(?:[\/\-](\d{2,4}))?\b',  # 2/15, 2/15/24
        r'\b(\d{1,2})(?:st|nd|rd|th)?\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b',  # 15th Feb
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\b',  # Feb 15th
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, query_lower)
        if match:
            try:
                # Try to parse the matched date string
                date_str = match.group(0)
                parsed_date = date_parser.parse(date_str, fuzzy=True, default=today)
                
                # If the parsed date is in the past this year, assume next year
                if parsed_date < today:
                    parsed_date = parsed_date.replace(year=today.year + 1)
                
                day_of_week = parsed_date.strftime('%A').lower()
                constraint = f"User wants experiences for {parsed_date.strftime('%A, %B %d, %Y')}. ONLY return experiences that are open/available on {day_of_week}s. Ensure the experience operates on this specific date."
                return parsed_date, day_of_week, constraint
            except (ValueError, TypeError):
                continue
    
    return None, None, None


# --- TIME PARSING UTILITY ---
def parse_time_from_query(query: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract time-related information from user query.
    
    Returns:
        Tuple of (time_of_day, time_constraint_text)
        - time_of_day: 'morning', 'afternoon', 'evening', 'night', or None
        - time_constraint_text: Human-readable constraint to add to prompt
    """
    query_lower = query.lower()
    
    # Time period patterns
    time_patterns = {
        'morning': ['morning', 'breakfast', 'sunrise', 'early', 'am', '6am', '7am', '8am', '9am', '10am', '11am'],
        'afternoon': ['afternoon', 'lunch', 'midday', 'noon', '12pm', '1pm', '2pm', '3pm', '4pm'],
        'evening': ['evening', 'sunset', 'dusk', '5pm', '6pm', '7pm', '8pm'],
        'night': ['night', 'dinner', 'late', 'midnight', '9pm', '10pm', '11pm', 'nightlife']
    }
    
    # Check for specific time ranges (e.g., "7pm-9pm")
    time_range_match = re.search(r'(\d{1,2})\s*(am|pm)?\s*[-–to]+\s*(\d{1,2})\s*(am|pm)?', query_lower)
    if time_range_match:
        start_hour = int(time_range_match.group(1))
        end_hour = int(time_range_match.group(3))
        start_period = time_range_match.group(2) or 'pm'
        end_period = time_range_match.group(4) or 'pm'
        
        # Convert to 24h for classification
        if start_period == 'pm' and start_hour != 12:
            start_hour += 12
        if start_hour < 12:
            time_of_day = 'morning'
        elif start_hour < 17:
            time_of_day = 'afternoon'
        elif start_hour < 21:
            time_of_day = 'evening'
        else:
            time_of_day = 'night'
        
        constraint = f"User wants experiences available between {time_range_match.group(0)}. Prioritize experiences that operate during this time window."
        return time_of_day, constraint
    
    # Check for weekend/weekday
    if 'weekend' in query_lower or 'saturday' in query_lower or 'sunday' in query_lower:
        constraint = "User prefers weekend activities. Focus on experiences available on Saturday/Sunday."
        # Determine time of day if also specified
        for period, keywords in time_patterns.items():
            if any(kw in query_lower for kw in keywords):
                return period, constraint
        return None, constraint
    
    if 'weekday' in query_lower or any(day in query_lower for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']):
        constraint = "User prefers weekday activities. Focus on experiences available on weekdays."
        for period, keywords in time_patterns.items():
            if any(kw in query_lower for kw in keywords):
                return period, constraint
        return None, constraint
    
    # Check for time periods
    for period, keywords in time_patterns.items():
        if any(kw in query_lower for kw in keywords):
            if period == 'morning':
                constraint = f"User wants {period} experiences (typically 6 AM - 12 PM). Focus on breakfast spots, sunrise activities, morning walks, or early workshops."
            elif period == 'afternoon':
                constraint = f"User wants {period} experiences (typically 12 PM - 5 PM). Focus on lunch spots, afternoon workshops, or daytime activities."
            elif period == 'evening':
                constraint = f"User wants {period} experiences (typically 5 PM - 9 PM). Focus on sunset spots, dinner options, or evening cultural activities."
            else:  # night
                constraint = f"User wants {period} experiences (typically after 9 PM). Focus on nightlife, late-night eateries, or evening performances."
            return period, constraint
    
    return None, None

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Agent Logger with global log writer
_agent_logger = AgentLogger("discovery_agent", log_writer=get_log_writer(), config=get_log_config())

# --- 1. SYSTEM PROMPT ---
DISCOVERY_SYSTEM_PROMPT = """You are the Discovery Agent for Sidequest, a plot-first experience discovery platform.

Your role is to find compelling, unique experiences based on the user's query and preferences.

Given the user's input, discover and return 10-15 relevant experiences. Focus on:
1. UNIQUE, LESSER-KNOWN GEMS that are NOT commonly featured on mainstream travel sites
2. Hyperlocal spots not easily found on Google Maps (specific artisan names, hidden cafes, specific workshops)
3. Artisan workshops, heritage walks, cultural immersions
4. Solo-friendly activities with social scaffolding potential
5. Experiences with story potential (lore, provenance, friction)

IMPORTANT: Avoid these well-known/commonly curated Bangalore spots (we already have them):
- CTR Malleshwaram, Vidyarthi Bhavan, Brahmin's Coffee Bar, MTR, Airlines Hotel
- Toit Brewery, The Humming Tree
- Cubbon Park Run Club, Lalbagh, Nandi Hills, Sankey Tank
- Bangalore Palace, Bull Temple, National Gallery of Modern Art
- Commercial Street, Clay Station

Instead, discover HIDDEN GEMS like:
- Neighborhood-specific darshinis and thindi streets
- Lesser-known artisan workshops (not the famous ones)
- Secret rooftops, basement bars, speakeasy-style venues
- Community-run cultural events
- Emerging neighborhoods with unique character
- Time-specific events (monthly markets, seasonal festivals)

CRITICAL: If a specific date or day is mentioned, ONLY return experiences that are ACTUALLY OPEN/AVAILABLE on that day.
- Check if the experience operates on the requested day of the week
- Consider if it's a weekend-only, weekday-only, or specific-day experience
- Do NOT include experiences that are closed on the requested date

CRITICAL: If a duration constraint is mentioned, respect the user's available time.
- Prioritize experiences that fit within the time window
- For limited time, quality over quantity — fewer, deeper experiences are better
- Consider travel time between experiences (15-30 mins in city traffic)

For each experience, provide:
- name: Experience name (be specific - include venue name if applicable)
- category: One of [food, craft, heritage, nature, art, music, fitness, shopping, networking]
- timing: Best time to visit (e.g., "Saturday 7 AM for fresh flowers")
- time_of_day: One of [morning, afternoon, evening, night, flexible] - when this experience is best enjoyed
- duration_hours: Estimated time to fully enjoy this experience (e.g., 1.5, 2, 3). Be realistic.
- operating_days: Array of days when open, e.g., ["monday", "tuesday", "wednesday", "thursday", "friday"] or ["saturday", "sunday"] or ["daily"]
- operating_hours: String describing hours, e.g., "10 AM - 6 PM" or "7 AM - 12 PM, 4 PM - 9 PM"
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
    time_available_hours = state.get("time_available_hours", 8.0)  # Default to 8 hours
    start_time = state.get("start_time", "10:00")
    
    # Parse time constraints from user query
    time_of_day, time_constraint = parse_time_from_query(user_query)
    
    # Parse date constraints from user query
    parsed_date, day_of_week, date_constraint = parse_date_from_query(user_query)
    
    logger.info("="*60)
    logger.info("🔍 DISCOVERY AGENT STARTED")
    logger.info(f"Query: {user_query}")
    logger.info(f"City: {city}")
    logger.info(f"Budget Range: ₹{budget_range}")
    logger.info(f"Interest Pods: {interest_pods}")
    if time_of_day:
        logger.info(f"Time Preference: {time_of_day}")
    if parsed_date:
        logger.info(f"Date Filter: {parsed_date.strftime('%A, %B %d, %Y')}")
    if day_of_week:
        logger.info(f"Day of Week: {day_of_week}")
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
    
    # Add time context if detected
    time_context = ""
    if time_constraint:
        time_context = f"\n\nTIME CONSTRAINT: {time_constraint}"
    
    # Add date context if detected
    date_context = ""
    if date_constraint:
        date_context = f"\n\nDATE CONSTRAINT: {date_constraint}"
        # Add today's date for reference
        date_context += f"\n(Today is {datetime.now().strftime('%A, %B %d, %Y')})"
    
    # Add duration constraint based on available time
    duration_context = ""
    if time_available_hours and time_available_hours < 8:
        # For limited time windows, prioritize shorter experiences
        max_single_exp_hours = min(time_available_hours / 2, 3)  # No single experience > half the total or 3 hours
        duration_context = f"""

DURATION CONSTRAINT: User has only {time_available_hours} hours available (starting at {start_time}).
- Prioritize experiences that take {max_single_exp_hours:.1f} hours or less each
- Total experiences should fit within {time_available_hours} hours including travel time (15-30 min between stops)
- For limited time, recommend 2-4 quality experiences rather than 5-10 rushed ones
- Include estimated duration for each experience in the response"""
    
    user_prompt = f"""
    User Request: {user_query}
    Target City: {city}
    Budget Range: ₹{budget_range}{interest_context}{time_context}{date_context}{duration_context}
    
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
            "city": city,
            "time_filter": time_of_day,
            "time_constraint_applied": time_constraint is not None,
            "date_filter": parsed_date.strftime('%Y-%m-%d') if parsed_date else None,
            "day_of_week": day_of_week,
            "date_constraint_applied": date_constraint is not None
        }
        
        experiences_count = len(result_json.get('discovered_experiences', []))
        logger.info(f"✨ Discovery Agent found {experiences_count} experiences")
        
        # Geocode all experiences to add coordinates
        if result_json.get('discovered_experiences'):
            logger.info("📍 Geocoding experience locations...")
            result_json['discovered_experiences'] = geocode_experiences(
                result_json['discovered_experiences'],
                city=city
            )
            logger.info("✅ Geocoding complete")
        
        # Post-process: Filter experiences by operating days if date constraint was applied
        if day_of_week and result_json.get('discovered_experiences'):
            logger.info(f"🗓️ Filtering experiences for {day_of_week}...")
            filtered_experiences = []
            
            for exp in result_json['discovered_experiences']:
                operating_days = exp.get('operating_days', ['daily'])
                
                # Normalize operating days to lowercase
                operating_days = [d.lower() for d in operating_days]
                
                # Check if experience is available on the requested day
                is_available = False
                
                if 'daily' in operating_days or 'all days' in operating_days:
                    is_available = True
                elif day_of_week == 'weekend':
                    is_available = 'saturday' in operating_days or 'sunday' in operating_days or 'weekends' in operating_days
                elif day_of_week in operating_days:
                    is_available = True
                elif day_of_week in ['saturday', 'sunday'] and 'weekends' in operating_days:
                    is_available = True
                elif day_of_week in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday'] and 'weekdays' in operating_days:
                    is_available = True
                
                if is_available:
                    filtered_experiences.append(exp)
                else:
                    logger.info(f"  ❌ Filtered out: {exp.get('name')} (not open on {day_of_week})")
            
            if len(filtered_experiences) < len(result_json['discovered_experiences']):
                logger.info(f"  Filtered: {len(result_json['discovered_experiences'])} → {len(filtered_experiences)} experiences")
            
            result_json['discovered_experiences'] = filtered_experiences
        
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