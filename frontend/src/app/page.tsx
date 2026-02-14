'use client';

import { useState, useMemo, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent } from '@/components/ui/card';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import {
  Sparkles,
  ChevronDown,
  ChevronUp,
  IndianRupee,
  UserCheck,
  MapPin,
  ArrowRight,
  Compass,
  Search,
  X,
} from 'lucide-react';
import { InterestPodSelector } from '@/components/filter-chips';
import { InputFormState, DiscoveryExperience } from '@/lib/types';
import { defaultFormState } from '@/lib/api';
import { cn } from '@/lib/utils';
import Link from 'next/link';
import {
  DiscoveryCard,
  DiscoveryCardSkeleton,
  CategoryTabs,
  WeatherWidget,
} from '@/components/discovery';
import { useExperiences } from '@/hooks/useExperiences';

// Quick filter options for explore section
const quickFilters = [
  { id: 'solo', label: 'Solo-friendly' },
  { id: 'under500', label: 'Under ₹500' },
  { id: 'free', label: 'Free' },
] as const;

export default function HomePage() {
  const router = useRouter();
  const [formState, setFormState] = useState<InputFormState>(defaultFormState);
  const [showPreferences, setShowPreferences] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Explore section state
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [activeQuickFilters, setActiveQuickFilters] = useState<string[]>([]);

  // Fetch experiences from API with auto-refresh
  const {
    experiences: allExperiences,
    isLoading,
    isFallback,
    refetch,
  } = useExperiences({
    fetchOnMount: true,
    useFallback: true,
    autoRefresh: true,
    refreshInterval: 60 * 1000, // Refresh every 60 seconds on home page
  });

  // Filter experiences for explore section
  const filteredExperiences = useMemo(() => {
    let results = [...allExperiences];

    // Category filter
    if (selectedCategory !== 'all') {
      results = results.filter((exp) => exp.category === selectedCategory);
    }

    // Search filter
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

    return results;
  }, [allExperiences, selectedCategory, searchQuery, activeQuickFilters]);

  const toggleQuickFilter = useCallback((id: string) => {
    setActiveQuickFilters((prev) =>
      prev.includes(id) ? prev.filter((f) => f !== id) : [...prev, id]
    );
  }, []);

  const handleExperienceSelect = (experience: DiscoveryExperience) => {
    sessionStorage.setItem('selected-experience', JSON.stringify(experience));
    const newFormState = {
      query: experience.name,
      socialMediaUrls: [],
      city: 'Bangalore',
      budgetMin: experience.budget.min,
      budgetMax: experience.budget.max,
      numPeople: 1,
      soloPreference: experience.solo_friendly.is_solo_sure,
      interestPods: [],
      crowdPreference: 'relatively_niche' as const,
    };
    sessionStorage.setItem('sidequest-form', JSON.stringify(newFormState));
    router.push('/generate');
  };

  const clearExploreFilters = () => {
    setSearchQuery('');
    setSelectedCategory('all');
    setActiveQuickFilters([]);
  };

  const hasActiveExploreFilters = searchQuery || selectedCategory !== 'all' || activeQuickFilters.length > 0;

  const handleSubmit = async () => {
    if (!formState.query.trim()) return;
    setIsSubmitting(true);
    sessionStorage.setItem('sidequest-form', JSON.stringify(formState));
    router.push('/generate');
  };

  const canSubmit = formState.query.trim().length > 0;

  return (
    <main className="min-h-screen bg-background">
      {/* Header */}
      <header className="max-w-3xl mx-auto px-4 pt-8 pb-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-primary" />
          <span className="font-semibold text-lg">Sidequest</span>
        </div>
        <a href="#explore">
          <Button variant="ghost" size="sm" className="gap-1.5 text-muted-foreground">
            <Compass className="h-4 w-4" />
            Explore
          </Button>
        </a>
      </header>

      {/* Hero */}
      <section className="max-w-3xl mx-auto px-4 pt-8 pb-16">
        <h1 className="text-3xl md:text-4xl font-bold text-center mb-3 tracking-tight">
          Plan your next adventure
        </h1>
        <p className="text-muted-foreground text-center mb-10 text-lg">
          Tell us what you're in the mood for. Our AI will craft the perfect itinerary.
        </p>

        {/* Input Card */}
        <Card className="shadow-sm">
          <CardContent className="p-5">
            <Textarea
              placeholder="e.g., Solo pottery workshop for beginners, or a heritage coffee walk..."
              className="min-h-[120px] resize-none text-base bg-muted/30 border-0"
              value={formState.query}
              onChange={(e) => setFormState((prev) => ({ ...prev, query: e.target.value }))}
            />

            {/* City */}
            <div className="flex items-center gap-2 mt-4 pt-4 border-t border-border/50">
              <MapPin className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Exploring in</span>
              <span className="text-sm font-medium">{formState.city}</span>
            </div>

            {/* Preferences toggle */}
            <button
              type="button"
              onClick={() => setShowPreferences(!showPreferences)}
              className="flex items-center justify-between w-full py-3 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              <span>Preferences</span>
              {showPreferences ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            </button>

            {showPreferences && (
              <div className="space-y-5 pb-2 animate-fade-in">
                {/* Budget */}
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <Label className="flex items-center gap-2 text-sm">
                      <IndianRupee className="h-4 w-4" />
                      Budget
                    </Label>
                    <span className="text-sm">
                      ₹{formState.budgetMin.toLocaleString('en-IN')} – ₹{formState.budgetMax.toLocaleString('en-IN')}
                    </span>
                  </div>
                  <Slider
                    min={200}
                    max={10000}
                    step={100}
                    value={[formState.budgetMin, formState.budgetMax]}
                    onValueChange={([min, max]) => setFormState((prev) => ({ ...prev, budgetMin: min, budgetMax: max }))}
                  />
                </div>

                {/* Solo */}
                <div className="flex items-center justify-between">
                  <Label htmlFor="solo" className="flex items-center gap-2 text-sm">
                    <UserCheck className="h-4 w-4" />
                    Solo-friendly only
                  </Label>
                  <Switch
                    id="solo"
                    checked={formState.soloPreference}
                    onCheckedChange={(checked) => setFormState((prev) => ({ ...prev, soloPreference: checked }))}
                  />
                </div>

                {/* Interests */}
                <div className="space-y-3">
                  <Label className="text-sm">Interests</Label>
                  <InterestPodSelector
                    selected={formState.interestPods}
                    onChange={(pods) => setFormState((prev) => ({ ...prev, interestPods: pods }))}
                  />
                </div>
              </div>
            )}

            {/* Submit */}
            <Button
              size="lg"
              className="w-full mt-4 h-11"
              disabled={!canSubmit || isSubmitting}
              onClick={handleSubmit}
            >
              {isSubmitting ? (
                <span className="flex items-center gap-2">
                  <span className="h-4 w-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  Creating...
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  Create itinerary
                  <ArrowRight className="h-4 w-4" />
                </span>
              )}
            </Button>
          </CardContent>
        </Card>

        {/* Features */}
        <div className="flex justify-center gap-6 mt-8 text-sm text-muted-foreground">
          <span>5 AI agents</span>
          <span>·</span>
          <span>Story-driven</span>
          <span>·</span>
          <span>Solo-friendly</span>
        </div>
      </section>

      {/* Explore Section */}
      <section id="explore" className="max-w-6xl mx-auto px-4 py-12 border-t border-border/50 scroll-mt-4">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-semibold mb-1 flex items-center gap-2">
              <Compass className="h-6 w-6 text-primary" />
              Explore Experiences
            </h2>
            <p className="text-muted-foreground">
              Or pick from curated local experiences to start your journey
            </p>
          </div>
          <WeatherWidget compact />
        </div>

        {/* Search */}
        <div className="mb-6">
          <div className="relative max-w-md">
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
        <div className="mb-6 -mx-4 px-4 overflow-x-auto">
          <CategoryTabs
            selected={selectedCategory}
            onSelect={setSelectedCategory}
          />
        </div>

        {/* Quick Filters */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2 flex-wrap">
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

          {hasActiveExploreFilters && (
            <Button
              variant="ghost"
              size="sm"
              onClick={clearExploreFilters}
              className="text-muted-foreground"
            >
              Clear all
            </Button>
          )}
        </div>

        {/* Results count */}
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-muted-foreground">
            {isLoading 
              ? 'Discovering experiences...' 
              : `${filteredExperiences.length} experience${filteredExperiences.length !== 1 ? 's' : ''}`
            }
            {isFallback && !isLoading && (
              <span className="ml-2 text-xs text-amber-600">(cached)</span>
            )}
          </p>
        </div>

        {/* Experience Grid */}
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
            <Button variant="outline" onClick={clearExploreFilters}>
              Clear filters
            </Button>
          </div>
        )}
      </section>

      {/* How it works */}
      <section className="max-w-3xl mx-auto px-4 py-16 border-t border-border/50">
        <h2 className="text-xl font-semibold text-center mb-10">How it works</h2>
        <div className="grid md:grid-cols-3 gap-8">
          {[
            { step: '1', title: 'Describe', text: 'Tell us a vibe, paste a reel, or describe what you want.' },
            { step: '2', title: 'AI plans', text: '5 agents collaborate to find and curate experiences.' },
            { step: '3', title: 'Explore', text: 'Get a story-driven itinerary with local insights.' },
          ].map((item) => (
            <div key={item.step} className="text-center">
              <div className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-primary text-primary-foreground text-sm font-semibold mb-3">
                {item.step}
              </div>
              <h3 className="font-medium mb-1">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.text}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Footer */}
      <footer className="max-w-3xl mx-auto px-4 py-6 text-center text-sm text-muted-foreground border-t border-border/50">
        Built for Google Gemini Hackathon 2026
      </footer>
    </main>
  );
}
