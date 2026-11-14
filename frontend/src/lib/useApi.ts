// Load data from the API, keeping the previous result while reloading.
import { useCallback, useEffect, useState } from "react";

export interface Loaded<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
  reload: () => void;
}

interface Result<T> {
  key: string;
  data: T | null;
  error: Error | null;
}

/** `deps` lists what `load` depends on (ids from the URL): plain strings or numbers. */
export function useApi<T>(
  load: () => Promise<T>,
  deps: readonly (string | number | undefined)[],
): Loaded<T> {
  const [version, setVersion] = useState(0);
  const key = JSON.stringify([...deps, version]);
  const [result, setResult] = useState<Result<T>>({ key: "", data: null, error: null });

  useEffect(() => {
    let active = true;
    load().then(
      (data) => {
        if (active) setResult({ key, data, error: null });
      },
      (reason: unknown) => {
        if (!active) return;
        const error = reason instanceof Error ? reason : new Error(String(reason));
        setResult((previous) => ({ key, data: previous.data, error }));
      },
    );
    return () => {
      active = false;
    };
    // `key` stands for the caller's dependencies.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  const reload = useCallback(() => setVersion((v) => v + 1), []);
  return { data: result.data, error: result.error, loading: result.key !== key, reload };
}
