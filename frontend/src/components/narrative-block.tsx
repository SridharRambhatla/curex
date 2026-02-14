'use client';

import { useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import {
  Clock,
  MapPin,
  IndianRupee,
  UserCheck,
  ChevronDown,
  ChevronUp,
  Calendar,
  Navigation,
  Info,
  Sparkles,
} from 'lucide-react';
import { ExperienceItem, CulturalContext, SocialScaffolding } from '@/lib/types';
import { cn } from '@/lib/utils';

interface NarrativeBlockProps {
  experience: ExperienceItem;
  index: number;
  narrativeText?: string;
  culturalContext?: CulturalContext[string];
  socialScaffolding?: SocialScaffolding[string];
  onMapFocus?: () => void;
  className?: string;
}

export function NarrativeBlock({
  experience,
  index,
  narrativeText,
  culturalContext,
  socialScaffolding,
  onMapFocus,
  className,
}: NarrativeBlockProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Toggle expansion when clicking on the card content area
  const handleCardClick = (e: React.MouseEvent) => {
    // Don't toggle if clicking on buttons or interactive elements
    const target = e.target as HTMLElement;
    if (target.closest('button') || target.closest('a')) {
      return;
    }
    setIsExpanded(!isExpanded);
  };

  return (
    <div className={cn('relative', className)}>
      {/* Timeline connector */}
      {index > 0 && (
        <div className="absolute left-6 -top-4 w-0.5 h-4 bg-border" />
      )}

      <div className="flex gap-4">
        {/* Timeline dot with number */}
        <div className="flex-shrink-0">
          <div className="w-12 h-12 rounded-full bg-primary text-primary-foreground flex items-center justify-center font-bold text-lg shadow-md">
            {index + 1}
          </div>
          {/* Vertical line to next item */}
          <div className="w-0.5 h-full bg-border mx-auto mt-2" />
        </div>

        {/* Content - clickable to expand */}
        <div 
          className={cn(
            "flex-grow pb-8 cursor-pointer rounded-lg transition-all duration-300",
            isExpanded && "bg-muted/30 -mx-3 px-3 py-3"
          )}
          onClick={handleCardClick}
        >
          {/* Header row with time and expand indicator */}
          <div className="flex items-center justify-between mb-3">
            <Badge 
              variant="outline" 
              className="bg-background border-primary/30 text-primary"
            >
              <Clock className="h-3 w-3 mr-1" />
              {experience.timing}
            </Badge>
            <div className="flex items-center gap-1 text-xs text-muted-foreground">
              {isExpanded ? (
                <>
                  <span>Click to collapse</span>
                  <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  <span>Click for details</span>
                  <ChevronDown className="h-3 w-3" />
                </>
              )}
            </div>
          </div>

          {/* Experience title */}
          <h3 className="text-xl font-semibold mb-2 group">
            {experience.name}
            <Button
              variant="ghost"
              size="sm"
              className="ml-2 opacity-0 group-hover:opacity-100 transition-opacity"
              onClick={(e) => {
                e.stopPropagation();
                onMapFocus?.();
              }}
            >
              <MapPin className="h-4 w-4" />
            </Button>
          </h3>

          {/* Location */}
          <div className="flex items-center gap-1 text-sm text-muted-foreground mb-4">
            <MapPin className="h-3.5 w-3.5" />
            <span>{experience.location}</span>
          </div>

          {/* Narrative text / Lore - truncated when collapsed */}
          <div className="prose prose-sm dark:prose-invert max-w-none mb-4">
            {narrativeText ? (
              <p className={cn(
                "text-foreground leading-relaxed transition-all duration-300",
                !isExpanded && "line-clamp-3"
              )}>
                {narrativeText}
              </p>
            ) : experience.lore ? (
              <p className={cn(
                "text-foreground leading-relaxed transition-all duration-300",
                !isExpanded && "line-clamp-3"
              )}>
                {experience.lore}
              </p>
            ) : experience.description && (
              <p className={cn(
                "text-foreground leading-relaxed transition-all duration-300",
                !isExpanded && "line-clamp-3"
              )}>
                {experience.description}
              </p>
            )}
          </div>

          {/* Quick info badges */}
          <div className="flex flex-wrap gap-2 mb-4">
            {/* Budget */}
            <Badge variant="secondary" className="bg-muted">
              <IndianRupee className="h-3 w-3 mr-1" />
              {experience.budget.toLocaleString('en-IN')}
            </Badge>

            {/* Solo-friendly */}
            {experience.solo_friendly && (
              <Badge className="bg-secondary/20 text-secondary-foreground border border-secondary/30">
                <UserCheck className="h-3 w-3 mr-1" />
                Solo-sure
                {socialScaffolding?.solo_percentage && (
                  <span className="ml-1 opacity-75">
                    ({socialScaffolding.solo_percentage} solo)
                  </span>
                )}
              </Badge>
            )}

            {/* Category */}
            <Badge variant="outline">
              {experience.category}
            </Badge>
          </div>

          {/* Expanded details section */}
          {isExpanded && (culturalContext || socialScaffolding) && (
            <Card className="mt-4 bg-muted/50 border-muted animate-fade-in">
              <CardContent className="p-4 space-y-3">
                {/* Full description if not shown in narrative */}
                {!narrativeText && experience.description && experience.lore && (
                  <>
                    <div className="flex gap-3">
                      <Info className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                      <div>
                        <p className="text-sm font-medium">About</p>
                        <p className="text-sm text-muted-foreground">{experience.description}</p>
                      </div>
                    </div>
                    <Separator className="my-2" />
                  </>
                )}

                {/* Cultural context */}
                {culturalContext && (
                  <>
                    {culturalContext.timing && (
                      <div className="flex gap-3">
                        <Clock className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Best Time</p>
                          <p className="text-sm text-muted-foreground">{culturalContext.timing}</p>
                        </div>
                      </div>
                    )}
                    {culturalContext.dress && (
                      <div className="flex gap-3">
                        <Sparkles className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Dress Code</p>
                          <p className="text-sm text-muted-foreground">{culturalContext.dress}</p>
                        </div>
                      </div>
                    )}
                    {culturalContext.transport && (
                      <div className="flex gap-3">
                        <Navigation className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Getting There</p>
                          <p className="text-sm text-muted-foreground">{culturalContext.transport}</p>
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* Social scaffolding */}
                {socialScaffolding && (
                  <>
                    {culturalContext && <Separator className="my-2" />}
                    {socialScaffolding.scaffolding && (
                      <div className="flex gap-3">
                        <UserCheck className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Social Vibe</p>
                          <p className="text-sm text-muted-foreground">{socialScaffolding.scaffolding}</p>
                        </div>
                      </div>
                    )}
                    {socialScaffolding.arrival_vibe && (
                      <p className="text-sm text-muted-foreground italic pl-7">
                        &ldquo;{socialScaffolding.arrival_vibe}&rdquo;
                      </p>
                    )}
                    {socialScaffolding.beginner_energy && (
                      <div className="flex gap-3">
                        <Sparkles className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-sm font-medium">Beginner Friendly</p>
                          <p className="text-sm text-muted-foreground">{socialScaffolding.beginner_energy}</p>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Action buttons - only show when expanded */}
          {isExpanded && (
            <div className="flex flex-wrap gap-2 mt-4 animate-fade-in">
              <Button 
                variant="outline" 
                size="sm"
                onClick={(e) => e.stopPropagation()}
              >
                <Calendar className="h-4 w-4 mr-2" />
                Add to Calendar
              </Button>
              <Button 
                variant="outline" 
                size="sm" 
                onClick={(e) => {
                  e.stopPropagation();
                  onMapFocus?.();
                }}
              >
                <Navigation className="h-4 w-4 mr-2" />
                Get Directions
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// Skeleton for loading state
export function NarrativeBlockSkeleton() {
  return (
    <div className="flex gap-4">
      <div className="flex-shrink-0">
        <div className="w-12 h-12 rounded-full skeleton" />
        <div className="w-0.5 h-32 skeleton mx-auto mt-2" />
      </div>
      <div className="flex-grow pb-8">
        <div className="h-6 w-24 skeleton rounded mb-3" />
        <div className="h-7 w-64 skeleton rounded mb-2" />
        <div className="h-4 w-32 skeleton rounded mb-4" />
        <div className="space-y-2 mb-4">
          <div className="h-4 w-full skeleton rounded" />
          <div className="h-4 w-full skeleton rounded" />
          <div className="h-4 w-3/4 skeleton rounded" />
        </div>
        <div className="flex gap-2">
          <div className="h-6 w-20 skeleton rounded" />
          <div className="h-6 w-24 skeleton rounded" />
        </div>
      </div>
    </div>
  );
}

// Collision suggestion card
interface CollisionSuggestionCardProps {
  title: string;
  experiences: string[];
  why: string;
}

export function CollisionSuggestionCard({
  title,
  experiences,
  why,
}: CollisionSuggestionCardProps) {
  return (
    <Card className="border-accent/30 bg-accent/5">
      <CardContent className="p-5">
        <div className="flex items-start gap-3">
          <div className="p-2 rounded-lg bg-accent/20 text-accent">
            <Sparkles className="h-5 w-5" />
          </div>
          <div>
            <h4 className="font-semibold text-lg mb-1">{title}</h4>
            <p className="text-sm text-muted-foreground mb-3">{why}</p>
            <div className="flex flex-wrap gap-2">
              {experiences.map((exp, i) => (
                <Badge key={i} variant="outline" className="border-accent/30">
                  {exp}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
