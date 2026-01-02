import { notFound } from "next/navigation";
import Link from "next/link";
import fs from "fs";
import path from "path";
import matter from "gray-matter";
import { MDXRemote } from "next-mdx-remote/rsc";
import SiteLayout from "@/components/SiteLayout";

interface PostPageProps {
  params: Promise<{
    slug: string;
  }>;
}

async function getPost(slug: string) {
  const postsDirectory = path.join(process.cwd(), "src/content/posts");
  const filePath = path.join(postsDirectory, `${slug}.mdx`);

  if (!fs.existsSync(filePath)) {
    return null;
  }

  const fileContent = fs.readFileSync(filePath, "utf8");
  const { data, content } = matter(fileContent);

  return {
    meta: {
      title: data.title || "Untitled",
      description: data.description || "",
      date: data.date || "",
      author: data.author,
      tags: data.tags,
    },
    content,
  };
}

export async function generateStaticParams() {
  const postsDirectory = path.join(process.cwd(), "src/content/posts");

  if (!fs.existsSync(postsDirectory)) {
    return [];
  }

  const filenames = fs.readdirSync(postsDirectory);

  return filenames
    .filter((filename) => filename.endsWith(".mdx"))
    .map((filename) => ({
      slug: filename.replace(/\.mdx$/, ""),
    }));
}

export default async function PostPage({ params }: PostPageProps) {
  const { slug } = await params;
  const post = await getPost(slug);

  if (!post) {
    notFound();
  }

  return (
    <SiteLayout>
      <div className="bg-gray-50 min-h-screen">
        <article className="max-w-3xl mx-auto px-4 py-12">
          <nav className="mb-8">
            <Link href="/learn" className="text-emerald-600 hover:text-emerald-700">
              &larr; Back to Articles
            </Link>
          </nav>

          <header className="mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">{post.meta.title}</h1>
            {post.meta.description && (
              <p className="text-xl text-gray-600 mb-4">{post.meta.description}</p>
            )}
            <div className="flex items-center gap-4 text-sm text-gray-500">
              {post.meta.date && (
                <time dateTime={post.meta.date}>
                  {new Date(post.meta.date).toLocaleDateString("en-US", {
                    year: "numeric",
                    month: "long",
                    day: "numeric",
                  })}
                </time>
              )}
              {post.meta.author && <span>By {post.meta.author}</span>}
            </div>
            {post.meta.tags && post.meta.tags.length > 0 && (
              <div className="flex gap-2 mt-4">
                {post.meta.tags.map((tag: string) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-emerald-50 text-emerald-700 text-xs rounded"
                  >
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </header>

          <div className="prose prose-lg prose-emerald max-w-none prose-headings:text-gray-900 prose-p:text-gray-700 prose-strong:text-gray-900 prose-li:text-gray-700">
            <MDXRemote source={post.content} />
          </div>
        </article>
      </div>
    </SiteLayout>
  );
}
