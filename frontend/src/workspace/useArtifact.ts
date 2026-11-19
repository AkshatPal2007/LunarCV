import { useEffect, useState } from "react";
import { artifact } from "./api";
export function useArtifact(path: string | undefined, key: string) {
  const [state, setState] = useState<{
    path?: string;
    credential?: string;
    url?: string;
    error?: string;
  }>({});
  useEffect(() => {
    if (!path) return;
    const abort = new AbortController();
    let url: string | undefined;
    artifact(path, key, abort.signal)
      .then((blob) => {
        if (abort.signal.aborted) return;
        url = URL.createObjectURL(blob);
        setState({ path, credential: key, url });
      })
      .catch((error: Error) => {
        if (!abort.signal.aborted)
          setState({ path, credential: key, error: error.message });
      });
    return () => {
      abort.abort();
      if (url) URL.revokeObjectURL(url);
    };
  }, [path, key]);
  return state.path === path && state.credential === key ? state : {};
}
