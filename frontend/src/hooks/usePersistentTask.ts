import { useCallback, useState } from "react";

export function usePersistentTask(key: string): [string | null, (value: string | null) => void] {
  const storageKey = `fip.task.${key}`;
  const [taskId, setTaskId] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(storageKey);
    } catch {
      return null;
    }
  });

  const update = useCallback(
    (value: string | null) => {
      setTaskId(value);
      try {
        if (value) window.localStorage.setItem(storageKey, value);
        else window.localStorage.removeItem(storageKey);
      } catch {
        // The active session still works when local persistence is unavailable.
      }
    },
    [storageKey],
  );
  return [taskId, update];
}
