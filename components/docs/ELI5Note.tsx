import { Lightbulb } from 'lucide-react';
import { ReactNode } from 'react';

interface ELI5NoteProps {
  children: ReactNode;
  title?: string;
}

export function ELI5Note({ children, title = "In Simple Terms" }: ELI5NoteProps) {
  return (
    <div className="my-6 p-4 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/30 rounded-lg">
      <div className="flex items-center gap-2 mb-2">
        <Lightbulb className="h-5 w-5 text-amber-600 dark:text-amber-400" />
        <h4 className="text-sm font-semibold text-amber-800 dark:text-amber-200 m-0">
          {title}
        </h4>
      </div>
      <div className="text-sm text-amber-800 dark:text-amber-100 leading-relaxed">
        {children}
      </div>
    </div>
  );
}