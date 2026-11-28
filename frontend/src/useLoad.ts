import { useCallback, useEffect, useRef, useState } from "react";
import { api, errorText } from "./api";

/** GET something from the API, with a readable error and a way to reload.
 *  If the path changes while a request is still running, the older answer is ignored. */
export function useLoad<T>(path: string | null) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const latest = useRef(0);

  const reload = useCallback(() => {
    if (!path) return;
    const request = ++latest.current;
    setError(null);
    api
      .get<T>(path)
      .then((d) => request === latest.current && setData(d))
      .catch((err) => request === latest.current && setError(errorText(err)));
  }, [path]);

  useEffect(() => {
    setData(null);
    reload();
  }, [reload]);

  return { data, error, reload, setData };
}
