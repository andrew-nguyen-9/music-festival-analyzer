import Link from "next/link";
import DraggableNotes from "@/components/DraggableNotes";

export default function NotFound() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-5 text-center">
      {/* ambient backdrop */}
      <div
        className="pointer-events-none absolute inset-0 -z-10"
        style={{
          background:
            "radial-gradient(60% 70% at 50% 35%, rgba(255,69,0,0.12), transparent 60%), radial-gradient(50% 60% at 80% 90%, rgba(123,47,190,0.12), transparent 60%)",
        }}
        aria-hidden
      />

      {/* draggable music glyphs fill the viewport behind the message */}
      <DraggableNotes />

      {/* message sits above, but lets pointer events fall through to notes
          except on the interactive button/links */}
      <div className="pointer-events-none relative z-10 flex flex-col items-center">
        <p className="text-label uppercase tracking-[0.3em] text-accent">
          Lost the beat
        </p>
        <h1 className="mt-4 text-[clamp(5rem,22vw,16rem)] font-extrabold leading-none tracking-tighter text-white">
          404
        </h1>
        <p className="mt-4 max-w-md text-body-lg text-[color:var(--text-muted)]">
          This page isn&apos;t on the lineup. Drag the notes around while
          you&apos;re here.
        </p>
        <Link
          href="/"
          className="pointer-events-auto mt-9 rounded-full bg-accent px-7 py-3.5 text-label font-semibold uppercase tracking-wide text-black transition-transform hover:scale-105"
        >
          Back to festivals
        </Link>
      </div>
    </section>
  );
}
