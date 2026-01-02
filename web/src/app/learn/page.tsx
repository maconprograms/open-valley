import Link from "next/link";
import fs from "fs";
import path from "path";
import matter from "gray-matter";
import SiteLayout from "@/components/SiteLayout";

interface PostMeta {
  slug: string;
  title: string;
  description: string;
  date: string;
  author?: string;
  tags?: string[];
}

async function getPosts(): Promise<PostMeta[]> {
  const postsDirectory = path.join(process.cwd(), "src/content/posts");

  if (!fs.existsSync(postsDirectory)) {
    return [];
  }

  const filenames = fs.readdirSync(postsDirectory);

  const posts = filenames
    .filter((filename) => filename.endsWith(".mdx"))
    .map((filename) => {
      const filePath = path.join(postsDirectory, filename);
      const fileContent = fs.readFileSync(filePath, "utf8");
      const { data } = matter(fileContent);

      return {
        slug: filename.replace(/\.mdx$/, ""),
        title: data.title || "Untitled",
        description: data.description || "",
        date: data.date || "",
        author: data.author,
        tags: data.tags,
      };
    })
    .sort((a, b) => {
      if (!a.date || !b.date) return 0;
      return new Date(b.date).getTime() - new Date(a.date).getTime();
    });

  return posts;
}

export const metadata = {
  title: "Learn - Open Valley",
  description: "Articles and guides about Warren, Vermont community data and local governance.",
};

export default async function LearnPage() {
  const posts = await getPosts();

  return (
    <SiteLayout>
      <div className="bg-gray-50 min-h-screen">
        <div className="max-w-4xl mx-auto px-4 py-12">
          <header className="mb-12">
            <h1 className="text-4xl font-bold text-gray-900 mb-4">
              Research &amp; Articles
            </h1>
            <p className="text-xl text-gray-600">
              Deep dives into Warren&apos;s housing data, Vermont policy, and our methodology.
            </p>
          </header>

          {posts.length === 0 ? (
            <div className="bg-white rounded-lg shadow-sm p-8 text-center">
              <p className="text-gray-500 mb-4">No posts yet. Check back soon!</p>
            </div>
          ) : (
            <div className="space-y-6">
              {posts.map((post) => (
                <article
                  key={post.slug}
                  className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow"
                >
                  <Link href={`/learn/${post.slug}`}>
                    <h2 className="text-2xl font-semibold text-gray-900 hover:text-emerald-600 mb-2">
                      {post.title}
                    </h2>
                  </Link>
                  {post.description && (
                    <p className="text-gray-600 mb-3">{post.description}</p>
                  )}
                  <div className="flex items-center gap-4 text-sm text-gray-500">
                    {post.date && (
                      <time dateTime={post.date}>
                        {new Date(post.date).toLocaleDateString("en-US", {
                          year: "numeric",
                          month: "long",
                          day: "numeric",
                        })}
                      </time>
                    )}
                    {post.author && <span>By {post.author}</span>}
                  </div>
                  {post.tags && post.tags.length > 0 && (
                    <div className="flex gap-2 mt-3">
                      {post.tags.map((tag) => (
                        <span
                          key={tag}
                          className="px-2 py-1 bg-emerald-50 text-emerald-700 text-xs rounded"
                        >
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </article>
              ))}
            </div>
          )}
        </div>
      </div>
    </SiteLayout>
  );
}
