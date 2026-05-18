import { useEffect, useState } from "react";

type ApiState<T> = {
  data: T | null;
  error: string | null;
  loading: boolean;
};

export function useApi<T>(load: () => Promise<T>, deps: React.DependencyList = []): ApiState<T> {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    error: null,
    loading: true,
  });

  useEffect(() => {
    let active = true;
    setState((current) => ({ ...current, error: null, loading: true }));
    load()
      .then((data) => {
        if (active) {
          setState({ data, error: null, loading: false });
        }
      })
      .catch((error: unknown) => {
        if (active) {
          const message = error instanceof Error ? error.message : "Request failed";
          setState({ data: null, error: message, loading: false });
        }
      });

    return () => {
      active = false;
    };
  }, deps);

  return state;
}
