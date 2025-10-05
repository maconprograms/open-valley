import { ArrowRight, Database, Cpu, FileText } from 'lucide-react';
import { ReactNode } from 'react';

interface LineageItem {
  label: string;
  href?: string;
  description?: string;
}

interface LineageCalloutProps {
  source: LineageItem;
  processedBy: LineageItem;
  reflectedIn: LineageItem;
  children?: ReactNode;
}

function LineageStep({ item, icon: Icon, isLast = false }: { 
  item: LineageItem; 
  icon: typeof Database; 
  isLast?: boolean;
}) {
  const content = (
    <div className="flex items-center gap-2">
      <Icon className="h-4 w-4 text-cyan-600 dark:text-cyan-400" />
      <div>
        <div className="font-medium text-sm">{item.label}</div>
        {item.description && (
          <div className="text-xs text-muted-foreground">{item.description}</div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex items-center gap-3">
      {item.href ? (
        <a 
          href={item.href} 
          className="text-cyan-700 hover:text-cyan-800 dark:text-cyan-300 dark:hover:text-cyan-200 no-underline"
        >
          {content}
        </a>
      ) : (
        content
      )}
      {!isLast && (
        <ArrowRight className="h-4 w-4 text-muted-foreground flex-shrink-0" />
      )}
    </div>
  );
}

export function LineageCallout({ source, processedBy, reflectedIn, children }: LineageCalloutProps) {
  return (
    <div className="my-6 p-4 bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-800/30 rounded-lg">
      <div className="flex items-center gap-2 mb-3">
        <Database className="h-5 w-5 text-cyan-600 dark:text-cyan-400" />
        <h4 className="text-sm font-semibold text-cyan-800 dark:text-cyan-200 m-0">
          Data Lineage
        </h4>
      </div>
      
      <div className="flex flex-col md:flex-row gap-4 text-sm">
        <LineageStep item={source} icon={Database} />
        <LineageStep item={processedBy} icon={Cpu} />
        <LineageStep item={reflectedIn} icon={FileText} isLast />
      </div>
      
      {children && (
        <div className="mt-3 pt-3 border-t border-cyan-200 dark:border-cyan-800/30 text-sm text-cyan-800 dark:text-cyan-100">
          {children}
        </div>
      )}
    </div>
  );
}