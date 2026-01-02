import type { MDXComponents } from "mdx/types";

// Custom components for MDX content
export function useMDXComponents(components: MDXComponents): MDXComponents {
  return {
    // Customize heading styles
    h1: ({ children }) => (
      <h1 className="text-4xl font-bold mb-6 text-gray-900">{children}</h1>
    ),
    h2: ({ children }) => (
      <h2 className="text-3xl font-semibold mb-4 mt-8 text-gray-800">{children}</h2>
    ),
    h3: ({ children }) => (
      <h3 className="text-2xl font-semibold mb-3 mt-6 text-gray-800">{children}</h3>
    ),
    // Paragraph styling
    p: ({ children }) => (
      <p className="mb-4 text-gray-700 leading-relaxed">{children}</p>
    ),
    // Link styling
    a: ({ href, children }) => (
      <a
        href={href}
        className="text-blue-600 hover:text-blue-800 underline"
        target={href?.startsWith("http") ? "_blank" : undefined}
        rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
      >
        {children}
      </a>
    ),
    // Code block styling
    pre: ({ children }) => (
      <pre className="bg-gray-100 rounded-lg p-4 overflow-x-auto mb-4 text-sm">
        {children}
      </pre>
    ),
    code: ({ children }) => (
      <code className="bg-gray-100 rounded px-1 py-0.5 text-sm font-mono">
        {children}
      </code>
    ),
    // List styling
    ul: ({ children }) => (
      <ul className="list-disc list-inside mb-4 space-y-1 text-gray-700">{children}</ul>
    ),
    ol: ({ children }) => (
      <ol className="list-decimal list-inside mb-4 space-y-1 text-gray-700">{children}</ol>
    ),
    // Blockquote styling
    blockquote: ({ children }) => (
      <blockquote className="border-l-4 border-blue-500 pl-4 italic text-gray-600 mb-4">
        {children}
      </blockquote>
    ),
    // Merge with any additional components passed in
    ...components,
  };
}
