"use client";

import { useReportWebVitals } from "next/web-vitals";

/**
 * Core Web Vitals reporting (v2.10.2/3). In dev it logs LCP/CLS/INP so
 * regressions are visible while building; in production it beacons to
 * NEXT_PUBLIC_VITALS_URL when configured (no-op otherwise). Renders nothing.
 */
export default function WebVitals() {
  useReportWebVitals((metric) => {
    const url = process.env.NEXT_PUBLIC_VITALS_URL;
    if (url && typeof navigator !== "undefined" && navigator.sendBeacon) {
      navigator.sendBeacon(url, JSON.stringify(metric));
    } else if (process.env.NODE_ENV !== "production") {
      // eslint-disable-next-line no-console
      console.log(
        `[web-vitals] ${metric.name} ${Math.round(metric.value)} (${metric.rating})`,
      );
    }
  });
  return null;
}
