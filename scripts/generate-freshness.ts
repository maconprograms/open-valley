#!/usr/bin/env node

import { promises as fs } from 'fs';
import { join } from 'path';

interface DatasetConfig {
  id: string;
  name: string;
  source: string;
  freshnessThreshold: {
    fresh: number; // hours
    stale: number; // hours
  };
}

interface FreshnessData {
  [key: string]: {
    lastUpdated: string;
    status: 'fresh' | 'stale' | 'critical' | 'unknown';
    source: string;
    name: string;
  };
}

// Configuration for datasets and their freshness thresholds
const datasets: DatasetConfig[] = [
  {
    id: 'property-data',
    name: 'Property Data',
    source: 'Warren Town Records',
    freshnessThreshold: { fresh: 24, stale: 168 } // fresh: 24h, stale after 7 days
  },
  {
    id: 'member-directory',
    name: 'Member Directory',
    source: 'Community Database',
    freshnessThreshold: { fresh: 72, stale: 504 } // fresh: 3 days, stale after 21 days
  },
  {
    id: 'updates-feed',
    name: 'Community Updates',
    source: 'Content Management System',
    freshnessThreshold: { fresh: 6, stale: 72 } // fresh: 6h, stale after 3 days
  },
  {
    id: 'external-api',
    name: 'External API Data',
    source: 'Third-party API',
    freshnessThreshold: { fresh: 12, stale: 48 } // fresh: 12h, stale after 2 days
  }
];

function calculateFreshnessStatus(lastUpdated: Date, thresholds: DatasetConfig['freshnessThreshold']): 'fresh' | 'stale' | 'critical' {
  const now = new Date();
  const diffInMs = now.getTime() - lastUpdated.getTime();
  const diffInHours = diffInMs / (1000 * 60 * 60);

  if (diffInHours <= thresholds.fresh) {
    return 'fresh';
  } else if (diffInHours <= thresholds.stale) {
    return 'stale';
  } else {
    return 'critical';
  }
}

async function getLastUpdateTime(datasetId: string): Promise<Date> {
  // In a real implementation, this would check:
  // - Database modification times
  // - API response timestamps
  // - File modification times
  // - Pipeline execution logs
  
  // For demo purposes, we'll simulate different update times
  const now = new Date();
  const mockDelays = {
    'property-data': 2 * 24 * 60 * 60 * 1000, // 2 days ago
    'member-directory': 7 * 24 * 60 * 60 * 1000, // 7 days ago
    'updates-feed': 2 * 60 * 60 * 1000, // 2 hours ago
    'external-api': 12 * 24 * 60 * 60 * 1000, // 12 days ago
  };

  const delay = mockDelays[datasetId as keyof typeof mockDelays] || 0;
  return new Date(now.getTime() - delay);
}

async function generateFreshnessData(): Promise<FreshnessData> {
  const freshnessData: FreshnessData = {};

  for (const dataset of datasets) {
    try {
      const lastUpdated = await getLastUpdateTime(dataset.id);
      const status = calculateFreshnessStatus(lastUpdated, dataset.freshnessThreshold);

      freshnessData[dataset.id] = {
        lastUpdated: lastUpdated.toISOString(),
        status,
        source: dataset.source,
        name: dataset.name
      };

      console.log(`✓ ${dataset.name}: ${status} (${lastUpdated.toISOString()})`);
    } catch (error) {
      console.error(`✗ Failed to get freshness for ${dataset.name}:`, error);
      freshnessData[dataset.id] = {
        lastUpdated: new Date().toISOString(),
        status: 'unknown',
        source: dataset.source,
        name: dataset.name
      };
    }
  }

  return freshnessData;
}

async function main() {
  console.log('🔄 Generating freshness data...');

  try {
    const freshnessData = await generateFreshnessData();
    
    // Ensure the public/docs directory exists
    const publicDocsDir = join(process.cwd(), 'public', 'docs');
    await fs.mkdir(publicDocsDir, { recursive: true });

    // Write the freshness data to JSON file
    const outputPath = join(publicDocsDir, 'freshness.json');
    await fs.writeFile(outputPath, JSON.stringify(freshnessData, null, 2), 'utf-8');

    console.log(`✅ Freshness data written to ${outputPath}`);
    console.log(`📊 Generated data for ${Object.keys(freshnessData).length} datasets`);

    // Summary by status
    const statusCounts = Object.values(freshnessData).reduce((acc, item) => {
      acc[item.status] = (acc[item.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    console.log('📈 Status summary:', statusCounts);

  } catch (error) {
    console.error('❌ Failed to generate freshness data:', error);
    process.exit(1);
  }
}

// Run the script if called directly
if (require.main === module) {
  main();
}

export { generateFreshnessData, datasets };