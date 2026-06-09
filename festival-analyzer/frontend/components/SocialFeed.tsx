"use client";

import { useMemo } from "react";
import Image from "next/image";
import EmptyState from "./EmptyState";
import { formatCount, timeAgo } from "@/lib/format";
import type { SocialPost } from "@/lib/types";

interface Props {
  posts: SocialPost[];
}

/**
 * Instagram-only social feed. (X/Twitter was removed for v1; Instagram
 * sync is on hold, so this shows an empty state until feed data lands.)
 */
export default function SocialFeed({ posts }: Props) {
  const visible = useMemo(
    () => posts.filter((p) => p.platform === "instagram"),
    [posts],
  );

  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <div className="mb-8 flex items-center gap-3">
        <h2 className="text-display-lg text-white">Social</h2>
        <span className="rounded-full border border-white/15 px-3 py-1 text-label uppercase tracking-wide text-white/60">
          Instagram
        </span>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title="Instagram feed coming soon"
          hint="Instagram sync is on hold for now — the latest posts will appear here once it's connected."
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {visible.map((post) => (
            <PostCard key={post.id} post={post} />
          ))}
        </div>
      )}
    </section>
  );
}

function PostCard({ post }: { post: SocialPost }) {
  return (
    <a
      href={post.post_url ?? "#"}
      target="_blank"
      rel="noreferrer"
      className="group flex flex-col overflow-hidden rounded-2xl border border-white/10 bg-surface-elevated transition-colors hover:border-white/25"
    >
      {post.media_url && (
        <div className="relative aspect-square w-full overflow-hidden">
          <Image
            src={post.media_url}
            alt=""
            fill
            sizes="(max-width: 640px) 100vw, 33vw"
            className="object-cover transition-transform duration-500 group-hover:scale-105"
          />
        </div>
      )}
      <div className="flex flex-1 flex-col p-4">
        {post.content && (
          <p className="line-clamp-3 text-body text-white/90">{post.content}</p>
        )}
        <div className="mt-auto flex items-center gap-4 pt-3 text-label text-[color:var(--text-muted)]">
          <span>{timeAgo(post.posted_at)}</span>
          {post.like_count != null && (
            <span>♥ {formatCount(post.like_count)}</span>
          )}
          {post.comment_count != null && (
            <span>💬 {formatCount(post.comment_count)}</span>
          )}
        </div>
      </div>
    </a>
  );
}
