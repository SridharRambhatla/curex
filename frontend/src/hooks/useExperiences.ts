'use client';

/**
 * useExperiences Hook
 * 
 * Fetches experiences from the Discovery API with fallback to sample data.
 * Supports progressive loading: shows curated data instantly, then enriches with agent data.
 * Handles loading, error states, caching, and auto-refresh.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { DiscoveryExperience } from '@/lib/types';
import { discoverExperiences, DiscoverRequest, DiscoverResponse } from '@/lib/api';
import { SAMPLE_EXPERIENCES } from '@/lib/sample-data';

interface UseExperiencesOptions {
  /** Initial request parameters */
  initialRequest?: DiscoverRequest;
  /** Whether to fetch on mount (default: true) */
  fetchOnMount?: boolean;
  /** Use sample data as fallback on API error (default: true) */
  useFallback?: boolean;
  /** Cache duration in ms (default: 5 minutes) */
  cacheDuration?: number;
  /** Enable auto-refresh polling (default: false) */
  autoRefresh?: boolean;
  /** Auto-refresh interval in ms (default: 30 seconds) */
  refreshInterval?: number;
  /** Enable progressive loading: curated first, then agent-enriched (default: true) */
  progressiveLoad?: boolean;
}

interface UseExperiencesReturn {
  experiences: DiscoveryExperience[];
  isLoading: boolean;
  error: Error | null;
  isFallback: boolean;
  totalCount: number;
  lastRefreshed: Date | null;
  isRefreshing: boolean;
  /** True when agent is fetching additional experiences in background */
  isEnriching: boolean;
  /** Source of current data: 'curated', 'agent', or 'hybrid' */
  source: 'curated' | 'agent' | 'hybrid' | 'fallback';
  /** Number of curated experiences */
  curatedCount: number;
  /** Number of agent-generated experiences */
  agentCount: number;
  refetch: (request?: DiscoverRequest) => Promise<void>;
}

// Simple in-memory cache
interface CacheEntry {
  data: DiscoveryExperience[];
  timestamp: number;
  totalCount: number;
  source: 'curated' | 'agent' | 'hybrid' | 'fallback';
  curatedCount: number;
  agentCount: number;
}
const cache = new Map<string, CacheEntry>();

function getCacheKey(request: DiscoverRequest): string {
  return JSON.stringify(request);
}

export function useExperiences(options: UseExperiencesOptions = {}): UseExperiencesReturn {
  const {
    initialRequest = {},
    fetchOnMount = true,
    useFallback = true,
    cacheDuration = 5 * 60 * 1000, // 5 minutes
    autoRefresh = false,
    refreshInterval = 30 * 1000, // 30 seconds
    progressiveLoad = true, // Enable two-phase loading by default
  } = options;

  const [experiences, setExperiences] = useState<DiscoveryExperience[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isEnriching, setIsEnriching] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [isFallback, setIsFallback] = useState(false);
  const [totalCount, setTotalCount] = useState(0);
  const [lastRefreshed, setLastRefreshed] = useState<Date | null>(null);
  const [source, setSource] = useState<'curated' | 'agent' | 'hybrid' | 'fallback'>('curated');
  const [curatedCount, setCuratedCount] = useState(0);
  const [agentCount, setAgentCount] = useState(0);
  
  // Track if component is mounted to avoid state updates after unmount
  const isMounted = useRef(true);
  const isPageVisible = useRef(true);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  // Helper to update state from response
  const updateFromResponse = useCallback((response: DiscoverResponse, sourceOverride?: 'curated' | 'agent' | 'hybrid' | 'fallback') => {
    setExperiences(response.experiences);
    setTotalCount(response.total_count);
    setSource(sourceOverride || response.source);
    setCuratedCount(response.curated_count);
    setAgentCount(response.agent_count);
    setIsFallback(false);
    setLastRefreshed(new Date());
  }, []);

  const fetchExperiences = useCallback(async (request: DiscoverRequest = {}, isBackgroundRefresh = false) => {
    const cacheKey = getCacheKey(request);
    
    // For background refresh, skip cache check to get fresh data
    if (!isBackgroundRefresh) {
      // Check cache first
      const cached = cache.get(cacheKey);
      if (cached && Date.now() - cached.timestamp < cacheDuration) {
        setExperiences(cached.data);
        setTotalCount(cached.totalCount);
        setSource(cached.source);
        setCuratedCount(cached.curatedCount);
        setAgentCount(cached.agentCount);
        setIsFallback(cached.source === 'fallback');
        setError(null);
        setLastRefreshed(new Date(cached.timestamp));
        return;
      }
    }

    // Use isRefreshing for background refresh, isLoading for initial load
    if (isBackgroundRefresh) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      if (progressiveLoad) {
        // Phase 1: Fetch curated data instantly
        const curatedResponse = await discoverExperiences({ ...request, fast_mode: true });
        
        if (!isMounted.current) return;
        
        // Show curated data immediately
        updateFromResponse(curatedResponse);
        setIsLoading(false);
        
        // Phase 2: Fetch hybrid data in background
        setIsEnriching(true);
        
        try {
          const hybridResponse = await discoverExperiences({ ...request, fast_mode: false });
          
          if (!isMounted.current) return;
          
          // Update with hybrid data
          updateFromResponse(hybridResponse);
          
          // Cache the hybrid result
          cache.set(cacheKey, {
            data: hybridResponse.experiences,
            totalCount: hybridResponse.total_count,
            timestamp: Date.now(),
            source: hybridResponse.source,
            curatedCount: hybridResponse.curated_count,
            agentCount: hybridResponse.agent_count,
          });
        } catch (enrichError) {
          // If enrichment fails, keep the curated data
          console.warn('Agent enrichment failed, keeping curated data:', enrichError);
          // Cache the curated result as fallback
          cache.set(cacheKey, {
            data: curatedResponse.experiences,
            totalCount: curatedResponse.total_count,
            timestamp: Date.now(),
            source: curatedResponse.source,
            curatedCount: curatedResponse.curated_count,
            agentCount: curatedResponse.agent_count,
          });
        } finally {
          if (isMounted.current) {
            setIsEnriching(false);
          }
        }
      } else {
        // Non-progressive: single request (hybrid mode)
        const response = await discoverExperiences(request);
        
        if (!isMounted.current) return;

        updateFromResponse(response);
        
        // Cache the result
        cache.set(cacheKey, {
          data: response.experiences,
          totalCount: response.total_count,
          timestamp: Date.now(),
          source: response.source,
          curatedCount: response.curated_count,
          agentCount: response.agent_count,
        });
      }
    } catch (err) {
      if (!isMounted.current) return;

      const error = err instanceof Error ? err : new Error('Failed to fetch experiences');
      setError(error);
      
      // Use sample data as fallback
      if (useFallback) {
        console.warn('Discovery API failed, using sample data as fallback:', error.message);
        setExperiences(SAMPLE_EXPERIENCES);
        setTotalCount(SAMPLE_EXPERIENCES.length);
        setSource('fallback');
        setCuratedCount(SAMPLE_EXPERIENCES.length);
        setAgentCount(0);
        setIsFallback(true);
      }
    } finally {
      if (isMounted.current) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [cacheDuration, useFallback, progressiveLoad, updateFromResponse]);

  // Handle visibility change for auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const handleVisibilityChange = () => {
      isPageVisible.current = document.visibilityState === 'visible';
      
      // When page becomes visible again, do a fresh fetch
      if (isPageVisible.current && isMounted.current) {
        const cacheKey = getCacheKey(initialRequest);
        cache.delete(cacheKey);
        fetchExperiences(initialRequest, true);
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [autoRefresh, fetchExperiences, initialRequest]);

  // Auto-refresh polling
  useEffect(() => {
    if (!autoRefresh || refreshInterval <= 0) return;

    intervalRef.current = setInterval(() => {
      // Only refresh if page is visible and not already loading
      if (isPageVisible.current && isMounted.current && !isRefreshing) {
        const cacheKey = getCacheKey(initialRequest);
        cache.delete(cacheKey);
        fetchExperiences(initialRequest, true);
      }
    }, refreshInterval);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [autoRefresh, refreshInterval, fetchExperiences, initialRequest, isRefreshing]);

  // Initial fetch on mount
  useEffect(() => {
    isMounted.current = true;
    
    if (fetchOnMount) {
      fetchExperiences(initialRequest);
    }

    return () => {
      isMounted.current = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const refetch = useCallback(async (request?: DiscoverRequest) => {
    // Clear cache for this request to force fresh fetch
    const cacheKey = getCacheKey(request || initialRequest);
    cache.delete(cacheKey);
    await fetchExperiences(request || initialRequest);
  }, [fetchExperiences, initialRequest]);

  return {
    experiences,
    isLoading,
    error,
    isFallback,
    totalCount,
    lastRefreshed,
    isRefreshing,
    isEnriching,
    source,
    curatedCount,
    agentCount,
    refetch,
  };
}

/**
 * Clear the experiences cache
 * Useful when you want to force fresh data
 */
export function clearExperiencesCache(): void {
  cache.clear();
}
