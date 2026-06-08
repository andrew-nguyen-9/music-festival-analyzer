"use client";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <html lang="en">
      <body
        style={{
          background: "#0A0A0A",
          color: "#fff",
          fontFamily: "system-ui, sans-serif",
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          padding: "2rem",
          textAlign: "center",
        }}
      >
        <h1 style={{ fontSize: "1.5rem", fontWeight: 600 }}>
          App-level error
        </h1>
        <pre
          style={{
            marginTop: "1rem",
            maxWidth: "42rem",
            overflow: "auto",
            border: "1px solid rgba(255,255,255,0.15)",
            borderRadius: "0.75rem",
            padding: "1rem",
            textAlign: "left",
            color: "#fca5a5",
            fontSize: "13px",
          }}
        >
          {error?.message || "Unknown error"}
          {error?.digest ? `\n\ndigest: ${error.digest}` : ""}
        </pre>
        <button
          onClick={reset}
          style={{
            marginTop: "1.5rem",
            background: "#FF4500",
            color: "#000",
            border: 0,
            borderRadius: "9999px",
            padding: "0.75rem 1.5rem",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          Try again
        </button>
      </body>
    </html>
  );
}
