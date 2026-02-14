/**
 * Sidequest - Shared TypeScript Types
 * Mirrors backend/state/schemas.py for type safety
 */

// ============================================
// API Request Types
// ============================================

export interface ItineraryRequest {
  query: string;
  social_media_urls?: string[];
  city?: string;
  budget_min?: number;
  budget_max?: number;
  num_people?: number;
  solo_preference?: boolean;
  interest_pods?: string[];
  crowd_preference?: 'crowded' | 'relatively_niche' | 'super_niche';
  start_date?: string;
  end_date?: string;
  /** Total hours available for the itinerary (e.g., 4, 6, 8) */
  time_available_hours?: number;
  /** Preferred start time (HH:MM format, e.g., '14:00' for 2 PM) */
  start_time?: string;
}

// ============================================
// API Response Types
// ============================================

export interface ExperienceItem {
  name: string;
  category: string;
  timing: string;
  budget: number;
  location: string;
  solo_friendly: boolean;
  source: string;
  lore: string;
  description: string;
  coordinates?: {
    lat: number;
    lng: number;
  };
}

export interface BudgetBreakdown {
  total_estimate: number;
  breakdown: BudgetItem[];
  deals: string[];
  within_budget: boolean;
}

export interface BudgetItem {
  experience?: string;
  cost: number;
  type: 'experience' | 'meal' | 'transport' | 'activity';
  booking_required?: string;
}

export interface CollisionSuggestion {
  title: string;
  experiences: string[];
  why: string;
}

export interface AgentTraceEntry {
  agent: string;
  status: 'started' | 'processing' | 'success' | 'error' | 'completed';
  timestamp: string;
  message?: string;
  latency_ms?: number;
  query?: string;
  city?: string;
  total_latency_ms?: number;
  agents_succeeded?: number;
  agents_failed?: number;
}

export interface SocialScaffolding {
  [experienceName: string]: {
    solo_friendly: boolean;
    solo_percentage: string;
    scaffolding: string;
    arrival_vibe: string;
    beginner_energy: string;
  };
}

export interface CulturalContext {
  [experienceName: string]: {
    timing: string;
    dress: string;
    transport: string;
    social: string;
    safety: string;
  };
}

export interface ItineraryResponse {
  narrative_itinerary: string;
  experiences: ExperienceItem[];
  cultural_context: CulturalContext;
  budget_breakdown: BudgetBreakdown | null;
  social_scaffolding: SocialScaffolding;
  collision_suggestion: CollisionSuggestion | null;
  agent_trace: AgentTraceEntry[];
  session_id: string;
}

// ============================================
// UI State Types
// ============================================

export interface InputFormState {
  query: string;
  socialMediaUrls: string[];
  city: string;
  budgetMin: number;
  budgetMax: number;
  numPeople: number;
  soloPreference: boolean;
  interestPods: string[];
  crowdPreference: 'crowded' | 'relatively_niche' | 'super_niche';
  startDate?: string;
  endDate?: string;
  /** Total hours available for the itinerary */
  timeAvailableHours?: number;
  /** Preferred start time (HH:MM format) */
  startTime?: string;
}

export type AgentStatus = 'waiting' | 'processing' | 'success' | 'error';

export interface AgentState {
  name: string;
  displayName: string;
  description: string;
  status: AgentStatus;
  progress: number;
  message?: string;
}

// ============================================
// Constants
// ============================================

export const INTEREST_PODS = [
  { id: 'food_nerd', label: 'Food & Drink', icon: 'utensils' },
  { id: 'craft_explorer', label: 'Crafts & Workshops', icon: 'palette' },
  { id: 'heritage_walker', label: 'Heritage & History', icon: 'landmark' },
  { id: 'fitness_enthusiast', label: 'Fitness & Wellness', icon: 'heart' },
  { id: 'art_culture', label: 'Art & Culture', icon: 'theater' },
  { id: 'nature_lover', label: 'Outdoors & Nature', icon: 'trees' },
  { id: 'nightlife', label: 'Nightlife & Music', icon: 'music' },
  { id: 'shopping', label: 'Shopping & Markets', icon: 'shopping-bag' },
] as const;

export const EXPERIENCE_CATEGORIES = [
  'Food & Drink',
  'Craft Workshop',
  'Heritage Walk',
  'Fitness',
  'Art & Culture',
  'Nature',
  'Nightlife',
  'Shopping',
] as const;

export const AGENTS = [
  {
    name: 'discovery',
    displayName: 'Discovery',
    description: 'Finding experiences from social media & local sources',
    icon: 'search',
  },
  {
    name: 'cultural_context',
    displayName: 'Cultural Context',
    description: 'Adding local timing, dress codes & transport tips',
    icon: 'globe',
  },
  {
    name: 'community',
    displayName: 'Community',
    description: 'Checking solo-friendliness & social vibes',
    icon: 'users',
  },
  {
    name: 'plot_builder',
    displayName: 'Plot Builder',
    description: 'Crafting your narrative journey with lore',
    icon: 'book-open',
  },
  {
    name: 'budget',
    displayName: 'Budget',
    description: 'Calculating costs & finding deals',
    icon: 'wallet',
  },
] as const;

export type AgentName = typeof AGENTS[number]['name'];

// ============================================
// Discovery Page Types
// ============================================

export interface DiscoveryExperience {
  id: string;
  name: string;
  category: string;
  description_short: string;
  image_url: string;
  location: {
    neighborhood: string;
    coordinates: { lat: number; lng: number };
  };
  timing: {
    type: 'flexible' | 'scheduled' | 'time_sensitive';
    duration_hours: number;
    advance_booking_required: boolean;
    advance_days_minimum?: number;
  };
  operating_days?: ('monday' | 'tuesday' | 'wednesday' | 'thursday' | 'friday' | 'saturday' | 'sunday' | 'daily' | 'weekdays' | 'weekends')[];
  operating_hours?: string;
  budget: { min: number; max: number; currency: 'INR' };
  solo_friendly: {
    is_solo_sure: boolean;
    confidence_score: number;
  };
  crowd_level: {
    current: 'low' | 'moderate' | 'high';
    updated_at: string;
  };
  weather_suitability: {
    indoor: boolean;
    outdoor: boolean;
    current_match: 'perfect' | 'good' | 'fair' | 'poor';
  };
  availability: {
    status: 'available' | 'limited' | 'sold_out';
    urgency_level: 'low' | 'medium' | 'high';
  };
  rating?: number;
  review_count?: number;
  bookmarked: boolean;
}

export interface WeatherData {
  temperature: number;
  condition: 'sunny' | 'cloudy' | 'rainy' | 'partly_cloudy' | 'thunderstorm';
  humidity: number;
  description: string;
  icon: string;
  recommendation: string;
}

export interface DiscoveryFilters {
  categories: string[];
  budgetRange: [number, number];
  soloFriendly: boolean;
  crowdPreference: 'any' | 'low' | 'moderate' | 'high';
  duration: 'any' | '1-2' | 'half-day' | 'full-day';
  weatherAppropriate: boolean;
}

// ============================================
// Gamification / Badges Types
// ============================================

export interface Badge {
  id: string;
  name: string;
  description: string;
  category: 'explorer' | 'behavior' | 'social';
  icon: string;
  requirement: number;
  current_progress: number;
  unlocked: boolean;
  unlocked_at?: string;
  tier: 'bronze' | 'silver' | 'gold';
}

export interface UserProfile {
  badges: Badge[];
  experiences_completed: number;
  neighborhoods_explored: string[];
  interest_pods_active: string[];
  total_spend: number;
  created_at: string;
}
