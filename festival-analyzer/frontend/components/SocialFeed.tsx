"use client";

import { useMemo, useState } from "react";
import Image from "next/image";
import EmptyState from "./EmptyState";
import { formatCount, timeAgo } from "@/lib/format";
import type { SocialPost, SocialPlatform } from "@/lib/types";

interface Props {
  posts: SocialPost[];
  defaultPlatform?: SocialPlatform;
}

export default function SocialFeed({
  posts,
  defaultPlatform = "instagram",
}: Props) {
  const [platform, setPlatform] = useState<SocialPlatform>(defaultPlatform);

  const visible = useMemo(
    () => posts.filter((p) => p.platform === platform),
    [posts, platform],
  );

  return (
    <section className="mx-auto max-w-wide px-5 py-16 md:px-8">
      <div className="mb-8 flex items-center justify-between">
        <h2 className="text-display-lg text-white">Social</h2>
        <div className="inline-flex rounded-full border border-white/15 p-1">
          <Tab
            label="Instagram"
            active={platform === "instagram"}
            onClick={() => setPlatform("instagram")}
          />
          <Tab
            label="X"
            active={platform === "x"}
            onClick={() => setPlatform("x")}
          />
        </div>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          title={`No ${platform === "x" ? "X" : "Instagram"} posts yet`}
          hint="Run pipeline/feed_syncer.py to pull the latest posts into the social_posts table."
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

function Tab({
  label,
  active,
  onClick,
}: {
  label: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-full px-4 py-1.5 text-label font-semibold uppercase tracking-wide transition-colors " +
        (active ? "bg-accent text-black" : "text-white/70 hover:text-white")
      }
    >
      {label}
    </button>
  );
}
