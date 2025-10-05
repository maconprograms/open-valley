import type { MDXComponents } from 'mdx/types';
import { ELI5Note } from './ELI5Note';
import { LineageCallout } from './LineageCallout';
import { FreshnessBadge } from './FreshnessBadge';

export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    // Custom MDX components for Warren VT documentation
    ELI5Note,
    LineageCallout,
    FreshnessBadge,
    
    // Base HTML elements with enhanced styling
    h1: ({ children, ...props }) => (
      <h1 className="text-4xl font-bold tracking-tight text-foreground mb-6" {...props}>
        {children}
      </h1>
    ),
    h2: ({ children, ...props }) => (
      <h2 className="text-3xl font-semibold tracking-tight text-foreground mb-4 mt-8" {...props}>
        {children}
      </h2>
    ),
    h3: ({ children, ...props }) => (
      <h3 className="text-2xl font-semibold tracking-tight text-foreground mb-3 mt-6" {...props}>
        {children}
      </h3>
    ),
    h4: ({ children, ...props }) => (
      <h4 className="text-xl font-semibold text-foreground mb-2 mt-4" {...props}>
        {children}
      </h4>
    ),
    p: ({ children, ...props }) => (
      <p className="leading-7 text-foreground mb-4" {...props}>
        {children}
      </p>
    ),
    ul: ({ children, ...props }) => (
      <ul className="ml-6 list-disc space-y-2 text-foreground mb-4" {...props}>
        {children}
      </ul>
    ),
    ol: ({ children, ...props }) => (
      <ol className="ml-6 list-decimal space-y-2 text-foreground mb-4" {...props}>
        {children}
      </ol>
    ),
    li: ({ children, ...props }) => (
      <li className="leading-7" {...props}>
        {children}
      </li>
    ),
    blockquote: ({ children, ...props }) => (
      <blockquote className="border-l-4 border-primary/50 pl-6 italic text-muted-foreground my-6" {...props}>
        {children}
      </blockquote>
    ),
    code: ({ children, ...props }) => (
      <code className="px-2 py-1 bg-muted rounded-md text-sm font-mono" {...props}>
        {children}
      </code>
    ),
    pre: ({ children, ...props }) => (
      <pre className="p-4 bg-muted rounded-lg overflow-x-auto text-sm font-mono mb-4" {...props}>
        {children}
      </pre>
    ),
    a: ({ children, href, ...props }) => (
      <a 
        href={href} 
        className="text-primary hover:text-primary/80 underline underline-offset-4 font-medium" 
        {...props}
      >
        {children}
      </a>
    ),
    table: ({ children, ...props }) => (
      <div className="overflow-x-auto mb-6">
        <table className="w-full border-collapse border border-border" {...props}>
          {children}
        </table>
      </div>
    ),
    th: ({ children, ...props }) => (
      <th className="border border-border px-4 py-2 bg-muted text-left font-semibold" {...props}>
        {children}
      </th>
    ),
    td: ({ children, ...props }) => (
      <td className="border border-border px-4 py-2" {...props}>
        {children}
      </td>
    ),
    hr: (props) => (
      <hr className="border-border my-8" {...props} />
    ),
    ...components,
  };
}