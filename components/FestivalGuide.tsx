import type { FestivalGuide as Guide } from "@/lib/types";

// Editorial festival guide (v3.9). Renders markdown body as paragraphs — no
// markdown dependency (ponytail: paragraph split covers authored prose; add a
// renderer only if guides start needing headings/lists/links). Nothing renders
// when there's no published guide.
export default function FestivalGuide({ guide }: { guide: Guide | null }) {
  if (!guide) return null;
  const paragraphs = guide.body_md.split(/\n\s*\n/).filter((p) => p.trim());
  return (
    <section className="mx-auto max-w-3xl px-5 py-16 md:px-8">
      <h2 className="mb-2 text-heading font-semibold text-white">{guide.title}</h2>
      {guide.author && (
        <p className="mb-6 text-xs uppercase tracking-[0.14em] text-white/40">
          By {guide.author}
        </p>
      )}
      <div className="space-y-4">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-body-lg leading-relaxed text-white/85">
            {p.trim()}
          </p>
        ))}
      </div>
    </section>
  );
}
