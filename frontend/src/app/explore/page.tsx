'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Sparkles,
  Search,
  X,
  RefreshCw,
  AlertCircle,
  Clock,
  Wand2,
  Zap,
} from 'lucide-react';
import {
  DiscoveryCard,
  DiscoveryCardSkeleton,
  WeatherWidget,
  CategoryTabs,
} from '@/components/discovery';
import { useExperiences } from '@/hooks/useExperiences';
import { DiscoveryExperience } from '@/lib/types';
import { cn } from '@/lib/utils';
import Link from 'next/link';

// Quick filter options
const quickFilters = [
  { id: 'solo', label: 'Solo-friendly' },
  { id: 'under500', label: 'Under ₹500' },
  { id: 'free', label: 'Free' },
] as const;

// Time filter options
const timeFilters = [
  { id: 'morning', label: 'Morning', description: '6 AM - 12 PM' },
  { id: 'afternoon', label: 'Afternoon', description: '12 PM - 5 PM' },
  { id: 'evening', label: 'Evening', description: '5 PM - 9 PM' },
  { id: 'night', label: 'Night', description: 'After 9 PM' },
] as const;

export default function ExplorePage() {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activeQuickFilters, setActiveQuickFilters] = useState<string[]>([]);
  const [selectedTimeFilter, setSelectedTimeFilter] = useState<string | null>(null);
  
  // Fetch experiences from API with fallback to sample data and auto-refresh
  // Progressive loading: shows curated data instantly, then enriches with AI-discovered experiences
  const { 
    experiences: allExperiences, 
    isLoading, 
    isRefreshing,
    isEnriching,
    error, 
    isFallback, 
    lastRefreshed,
    source,
    curatedCount,
    agentCount,
    refetch 
  } = useExperiences({
    fetchOnMount: true,
    useFallback: true,
    autoRefresh: true,
    refreshInterval: 60 * 1000, // Refresh every 60 seconds
    progressiveLoad: true, // Enable two-phase loading
  });

  // Format last refreshed time
  const formatLastRefreshed = (date: Date | null): string => {
    if (!date) return '';
    const now = new Date();
    const diffSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);
    
    if (diffSeconds < 10) return 'just now';
    if (diffSeconds < 60) return `${diffSeconds}s ago`;
    if (diffSeconds < 3600) return `${Math.floor(diffSeconds / 60)}m ago`;
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  // Helper to determine time of day for an experience
  const getTimeOfDay = (exp: DiscoveryExperience): string[] => {
    const name = exp.name.toLowerCase();
    const desc = exp.description_short.toLowerCase();
    const combined = `${name} ${desc}`;
    
    const times: string[] = [];
    
    // Morning indicators
    if (combined.includes('morning') || combined.includes('sunrise') || 
        combined.includes('breakfast') || combined.includes('6am') || 
        combined.includes('7am') || combined.includes('run club')) {
      times.push('morning');
    }
    
    // Afternoon indicators  
    if (combined.includes('afternoon') || combined.includes('lunch') ||
        exp.timing.type === 'flexible') {
      times.push('afternoon');
    }
    
    // Evening indicators
    if (combined.includes('evening') || combined.includes('sunset') ||
        combined.includes('dusk') || combined.includes('golden hour')) {
      times.push('evening');
    }
    
    // Night indicators
    if (combined.includes('night') || combined.includes('concert') ||
        combined.includes('nightlife') || combined.includes('dinner') ||
        exp.category === 'Nightlife') {
      times.push('night');
    }
    
    // Default: flexible experiences work for afternoon
    if (times.length === 0 && exp.timing.type === 'flexible') {
      return ['morning', 'afternoon', 'evening'];
    }
    
    return times.length > 0 ? times : ['afternoon']; // Default to afternoon
  };

  // Filter experiences (client-side filtering on fetched data)
  const filteredExperiences = useMemo(() => {
    let results = [...allExperiences];

    // Category
    if (selectedCategory !== 'all') {
      results = results.filter((exp) => exp.category === selectedCategory);
    }

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      results = results.filter(
        (exp) =>
          exp.name.toLowerCase().includes(q) ||
          exp.description_short.toLowerCase().includes(q) ||
          exp.location.neighborhood.toLowerCase().includes(q)
      );
    }

    // Quick filters
    activeQuickFilters.forEach((f) => {
      if (f === 'solo') results = results.filter((e) => e.solo_friendly.is_solo_sure);
      if (f === 'under500') results = results.filter((e) => e.budget.max <= 500);
      if (f === 'free') results = results.filter((e) => e.budget.max === 0);
    });

    // Time filter
    if (selectedTimeFilter) {
      results = results.filter((exp) => {
        const expTimes = getTimeOfDay(exp);
        return expTimes.includes(selectedTimeFilter);
      });
    }

    return results;
  }, [allExperiences, selectedCategory, searchQuery, activeQuickFilters, selectedTimeFilter]);

  const toggleQuickFilter = useCallback((id: string) => {
    setActiveQuickFilters((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
  }, []);

  const handleExperienceSelect = (experience: DiscoveryExperience) => {
    // Store experience in sessionStorage for the details page
    sessionStorage.setItem('selected-experience', JSON.stringify(experience));
    // Navigate directly to experience details page - no agent execution needed
    router.push(`/experience/${experience.id}`);
  };

  const clearFilters = () => {
    setSearchQuery('');
    setSelectedCategory('all');
    setActiveQuickFilters([]);
    setSelectedTimeFilter(null);
  };

  const hasActiveFilters = searchQuery || selectedCategory !== 'all' || activeQuickFilters.length > 0 || selectedTimeFilter !== null;

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur border-b border-border/50">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          {/* Top bar */}
          <div className="flex items-center justify-between h-14">
            <Link href="/" className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              <span className="font-semibold text-lg">Sidequest</span>
            </Link>
            <WeatherWidget compact />
          </div>

          {/* Search */}
          <div className="pb-3">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                type="text"
                placeholder="Search experiences..."
                className="pl-10 h-10 bg-muted/50 border-0 focus-visible:ring-1"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
              {searchQuery && (
                <Button
                  variant="ghost"
                  size="icon"
                  className="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8"
                  onClick={() => setSearchQuery('')}
                >
                  <X className="h-4 w-4" />
                </Button>
              )}
            </div>
          </div>

          {/* Categories */}
          <div className="pb-3 -mx-4 px-4">
            <CategoryTabs
              selected={selectedCategory}
              onSelect={setSelectedCategory}
            />
          </div>
        </div>
      </header>

      {/* Content */}
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-6">
        {/* Filters row */}
        <div className="space-y-4 mb-6">
          {/* Quick filters */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              {quickFilters.map((filter) => (
                <button
                  key={filter.id}
                  onClick={() => toggleQuickFilter(filter.id)}
                  className={cn(
                    'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                    activeQuickFilters.includes(filter.id)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:text-foreground'
                  )}
                >
                  {filter.label}
                </button>
              ))}
            </div>

            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="text-muted-foreground"
              >
                Clear all
              </Button>
            )}
          </div>
          
          {/* Time filters */}
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground mr-1">Time:</span>
            {timeFilters.map((filter) => (
              <button
                key={filter.id}
                onClick={() => setSelectedTimeFilter(
                  selectedTimeFilter === filter.id ? null : filter.id
                )}
                className={cn(
                  'px-3 py-1.5 rounded-full text-sm font-medium transition-colors',
                  selectedTimeFilter === filter.id
                    ? 'bg-secondary text-secondary-foreground'
                    : 'bg-muted/50 text-muted-foreground hover:text-foreground hover:bg-muted'
                )}
                title={filter.description}
              >
                {filter.label}
              </button>
            ))}
          </div>
        </div>

        {/* Status indicators */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <p className="text-sm text-muted-foreground">
              {isLoading 
                ? 'Loading curated experiences...' 
                : `${filteredExperiences.length} experience${filteredExperiences.length !== 1 ? 's' : ''}`
              }
            </p>
            {lastRefreshed && !isLoading && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                <Clock className="h-3 w-3" />
                Updated {formatLastRefreshed(lastRefreshed)}
              </span>
            )}
            {/* Source breakdown - show when we have data */}
            {!isLoading && source === 'hybrid' && (
              <span className="flex items-center gap-1 text-xs text-muted-foreground">
                ({curatedCount} curated + {agentCount} AI-discovered)
              </span>
            )}
          </div>
          
          <div className="flex items-center gap-2">
            {isFallback && !isLoading && (
              <span className="flex items-center gap-1 text-xs text-amber-600 bg-amber-50 dark:bg-amber-950/50 px-2 py-1 rounded-full">
                <AlertCircle className="h-3 w-3" />
                Using cached data
              </span>
            )}
            {/* AI Enriching indicator - shows while agent discovers more experiences */}
            {isEnriching && (
              <span className="flex items-center gap-1.5 text-xs text-violet-600 bg-violet-50 dark:bg-violet-950/50 px-2.5 py-1 rounded-full animate-pulse">
                <Wand2 className="h-3 w-3 animate-bounce" />
                AI discovering more...
              </span>
            )}
            {isRefreshing && !isEnriching && (
              <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 dark:bg-blue-950/50 px-2 py-1 rounded-full">
                <RefreshCw className="h-3 w-3 animate-spin" />
                Refreshing...
              </span>
            )}
            {/* Show hybrid badge when enriched with AI */}
            {!isLoading && !isEnriching && source === 'hybrid' && agentCount > 0 && (
              <span className="flex items-center gap-1 text-xs text-emerald-600 bg-emerald-50 dark:bg-emerald-950/50 px-2 py-1 rounded-full">
                <Zap className="h-3 w-3" />
                AI-enriched
              </span>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => refetch()}
              disabled={isLoading || isRefreshing || isEnriching}
              className="text-muted-foreground"
            >
              <RefreshCw className={cn("h-4 w-4 mr-1", (isLoading || isRefreshing || isEnriching) && "animate-spin")} />
              Refresh
            </Button>
          </div>
        </div>

        {/* Error display */}
        {error && !isFallback && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
            <p className="text-red-700 text-sm">{error.message}</p>
            <Button 
              variant="outline" 
              size="sm" 
              className="mt-2"
              onClick={() => refetch()}
            >
              Try again
            </Button>
          </div>
        )}

        {/* Grid */}
        {isLoading ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {Array.from({ length: 6 }).map((_, i) => (
              <DiscoveryCardSkeleton key={i} />
            ))}
          </div>
        ) : filteredExperiences.length > 0 ? (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {filteredExperiences.map((experience) => (
              <DiscoveryCard
                key={experience.id}
                experience={experience}
                onSelect={() => handleExperienceSelect(experience)}
              />
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <p className="text-muted-foreground mb-4">No experiences found</p>
            <Button variant="outline" onClick={clearFilters}>
              Clear filters
            </Button>
          </div>
        )}
      </div>
    </main>
  );
}
