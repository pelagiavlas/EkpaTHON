import { useCallback, useEffect, useState } from "react";
import { api, errorText } from "./api";

/** GET something from the API, with a readable error and a way to reload. */
export function useLoad<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!path) return;
    setError(null);
    api
      .get<T>(path)
      .then(setData)
      .catch((err) => setError(errorText(err)));
  }, [path]);

  useEffect(() => {
    setData(null);
    reload();
  }, [reload]);

  return { data, error, reload, setData };
}
