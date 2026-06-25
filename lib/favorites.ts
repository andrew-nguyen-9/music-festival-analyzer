// ─────────────────────────────────────────────────────────────
// Favorites store (v2.7.3) — starred artists, persisted in IndexedDB.
//
// Local-only by design: Festival Analyzer has no user-write backend (RLS is
// public-read; all writes go through the service-role pipeline), so favorites
// live on-device and are fully available offline — which is exactly the
// muddy-field, no-signal use case v2.7 targets.
//
// ponytail: raw IndexedDB, no `idb` dependency — the surface is one object
// store with get/put/delete/getAll, not worth a package. There is no server
// background-sync target (v2.7.4); when a user-data backend lands (v3), flush
// queued favorites from here. A tiny pub/sub keeps components in sync.
// ─────────────────────────────────────────────────────────────

export interface Favorite {
  id: string; // artist id
  slug: string;
  name: string;
  savedAt: number; // epoch ms
}

const DB_NAME = "festival-analyzer";
const DB_VERSION = 1;
const STORE = "favorites";

function hasIDB(): boolean {
  return typeof indexedDB !== "undefined";
}

let dbPromise: Promise<IDBDatabase> | null = null;

function openDB(): Promise<IDBDatabase> {
  if (dbPromise) return dbPromise;
  dbPromise = new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: "id" });
      }
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
  return dbPromise;
}

function tx<T>(
  mode: IDBTransactionMode,
  run: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  return openDB().then(
    (db) =>
      new Promise<T>((resolve, reject) => {
        const store = db.transaction(STORE, mode).objectStore(STORE);
        const req = run(store);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      }),
  );
}

export async function listFavorites(): Promise<Favorite[]> {
  if (!hasIDB()) return [];
  try {
    const all = await tx<Favorite[]>("readonly", (s) => s.getAll());
    return all.sort((a, b) => b.savedAt - a.savedAt);
  } catch {
    return [];
  }
}

export async function isFavorite(id: string): Promise<boolean> {
  if (!hasIDB()) return false;
  try {
    const row = await tx<Favorite | undefined>("readonly", (s) => s.get(id));
    return row != null;
  } catch {
    return false;
  }
}

/** Toggles a favorite. Returns the new state (true = now favorited). */
export async function toggleFavorite(
  fav: Omit<Favorite, "savedAt">,
): Promise<boolean> {
  if (!hasIDB()) return false;
  const exists = await isFavorite(fav.id);
  try {
    if (exists) {
      await tx("readwrite", (s) => s.delete(fav.id));
    } else {
      await tx("readwrite", (s) =>
        s.put({ ...fav, savedAt: Date.now() } satisfies Favorite),
      );
    }
    emit();
    return !exists;
  } catch {
    return exists;
  }
}

// ── pub/sub so every FavoriteButton / favorites list reacts to a change ──
const listeners = new Set<() => void>();

export function subscribeFavorites(cb: () => void): () => void {
  listeners.add(cb);
  return () => listeners.delete(cb);
}

function emit(): void {
  listeners.forEach((cb) => cb());
}
