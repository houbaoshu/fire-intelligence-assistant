import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import type { RecordStatus } from "@/lib/services/common";

/**
 * 业务记录详情编辑的共享逻辑:加载详情、本地草稿表单、脏标记、保存与状态流转。
 * 仅在服务端记录实际变化(id + updated_at 变化)时重置表单,后台 refetch 不覆盖未保存编辑。
 */
export function useRecordEditor<
  TDetail extends { id: string; updated_at: string; status: RecordStatus },
  TForm,
  TPayload,
>(config: {
  queryKey: readonly unknown[];
  fetchDetail: (signal?: AbortSignal) => Promise<TDetail>;
  toForm: (detail: TDetail) => TForm;
  buildPayload: (form: TForm) => TPayload;
  updateRecord: (payload: TPayload) => Promise<TDetail>;
  setStatus: (status: RecordStatus) => Promise<TDetail>;
}) {
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: config.queryKey,
    queryFn: ({ signal }) => config.fetchDetail(signal),
  });
  const detail = query.data;

  const [form, setForm] = useState<TForm | null>(null);
  const [dirty, setDirty] = useState(false);
  const [baseStamp, setBaseStamp] = useState<string | null>(null);

  useEffect(() => {
    if (!detail) return;
    const stamp = `${detail.id}:${detail.updated_at}`;
    if (stamp !== baseStamp) {
      setForm(config.toForm(detail));
      setBaseStamp(stamp);
      setDirty(false);
    }
  }, [detail, baseStamp, config]);

  const save = useMutation({
    mutationFn: () => {
      if (!form) throw new Error("表单尚未加载完成");
      return config.updateRecord(config.buildPayload(form));
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(config.queryKey, saved);
      toast.success("已保存");
    },
  });

  const transition = useMutation({
    mutationFn: (status: RecordStatus) => config.setStatus(status),
    onSuccess: (saved) => {
      queryClient.setQueryData(config.queryKey, saved);
      toast.success("状态已更新");
    },
  });

  const update = (fn: (f: TForm) => TForm) => {
    setForm((f) => (f ? fn(f) : f));
    setDirty(true);
  };

  const discard = () => {
    if (!detail) return;
    setForm(config.toForm(detail));
    setDirty(false);
    save.reset();
  };

  // 有未保存更改时,关闭 / 刷新页面前提示。
  useEffect(() => {
    if (!dirty) return;
    const handler = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", handler);
    return () => window.removeEventListener("beforeunload", handler);
  }, [dirty]);

  return { query, detail, form, dirty, update, discard, save, transition };
}
