import { useCallback, useState } from "react";

/**
 * 进行中的生成任务持久化(specs/_common.md:页面刷新或重进后可恢复进度展示)。
 * 任务 ID 存 localStorage;页面重新进入时继续轮询,进入终态后由调用方清除。
 */
export function useResumableTask(storageKey: string) {
  const key = `fip.pending-task.${storageKey}`;
  const [taskId, setTaskIdState] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  });

  const setTaskId = useCallback(
    (id: string | null) => {
      setTaskIdState(id);
      try {
        if (id) window.localStorage.setItem(key, id);
        else window.localStorage.removeItem(key);
      } catch {
        /* ignore */
      }
    },
    [key],
  );

  return { taskId, setTaskId };
}
