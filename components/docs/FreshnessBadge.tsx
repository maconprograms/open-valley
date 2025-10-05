import { Clock, CheckCircle, AlertCircle, XCircle } from 'lucide-react';
import { Badge } from '@/components/ui/badge';

interface FreshnessBadgeProps {
  datasetId: string;
  showLabel?: boolean;
  className?: string;
}

interface FreshnessData {
  [key: string]: {
    lastUpdated: string;
    status: 'fresh' | 'stale' | 'critical' | 'unknown';
  };
}

// This would normally be loaded from a JSON file or API
// For now, we'll use a mock dataset
const mockFreshnessData: FreshnessData = {
  'property-data': {
    lastUpdated: '2025-08-25T10:30:00Z',
    status: 'fresh'
  },
  'member-directory': {
    lastUpdated: '2025-08-20T14:15:00Z',
    status: 'stale'
  },
  'updates-feed': {
    lastUpdated: '2025-08-27T06:00:00Z',
    status: 'fresh'
  },
  'external-api': {
    lastUpdated: '2025-08-15T09:00:00Z',
    status: 'critical'
  }
};

function getTimeSince(dateString: string): string {
  const now = new Date();
  const past = new Date(dateString);
  const diffInMs = now.getTime() - past.getTime();
  const diffInDays = Math.floor(diffInMs / (1000 * 60 * 60 * 24));
  const diffInHours = Math.floor(diffInMs / (1000 * 60 * 60));
  
  if (diffInDays > 0) {
    return `${diffInDays} day${diffInDays === 1 ? '' : 's'} ago`;
  } else if (diffInHours > 0) {
    return `${diffInHours} hour${diffInHours === 1 ? '' : 's'} ago`;
  } else {
    return 'Just now';
  }
}

function getFreshnessVariant(status: string) {
  switch (status) {
    case 'fresh':
      return 'default'; // Using default which will be styled with primary color
    case 'stale':
      return 'secondary';
    case 'critical':
      return 'destructive';
    default:
      return 'outline';
  }
}

function getFreshnessIcon(status: string) {
  switch (status) {
    case 'fresh':
      return CheckCircle;
    case 'stale':
      return AlertCircle;
    case 'critical':
      return XCircle;
    default:
      return Clock;
  }
}

export function FreshnessBadge({ datasetId, showLabel = true, className = '' }: FreshnessBadgeProps) {
  const freshnessInfo = mockFreshnessData[datasetId];
  
  if (!freshnessInfo) {
    return (
      <Badge variant="outline" className={`gap-1 ${className}`}>
        <Clock className="h-3 w-3" />
        {showLabel && 'Unknown'}
      </Badge>
    );
  }
  
  const Icon = getFreshnessIcon(freshnessInfo.status);
  const variant = getFreshnessVariant(freshnessInfo.status);
  const timeAgo = getTimeSince(freshnessInfo.lastUpdated);
  
  return (
    <Badge variant={variant} className={`gap-1 ${className}`} title={`Last updated: ${timeAgo}`}>
      <Icon className="h-3 w-3" />
      {showLabel && (
        <span className="text-xs">
          {freshnessInfo.status === 'fresh' && 'Fresh'}
          {freshnessInfo.status === 'stale' && 'Stale'}
          {freshnessInfo.status === 'critical' && 'Critical'}
          {freshnessInfo.status === 'unknown' && 'Unknown'}
          {' • '}
          {timeAgo}
        </span>
      )}
    </Badge>
  );
}