import type { SourceCitation } from "@/lib/services/qa";

/** 来源元数据行:条款 / 页码 / 生效日期,逐项判空(只展示契约字段)。 */
export function sourceMetaLine(s: SourceCitation): string {
  const parts: string[] = [];
  if (s.article) parts.push(s.article);
  if (s.page != null) parts.push(`第 ${s.page} 页`);
  if (s.effective_date) parts.push(`生效日期 ${s.effective_date}`);
  return parts.join(" · ");
}

/** 复制用纯文本来源清单(specs/regulation-qa.md:复制必须包含可读的来源清单)。 */
export function formatSourcesForCopy(sources: SourceCitation[]): string {
  return sources
    .map((s, i) => {
      const meta = sourceMetaLine(s);
      const lines = [`[${i + 1}] ${s.title}`];
      if (meta) lines.push(`    ${meta}`);
      if (s.excerpt) lines.push(`    摘录:${s.excerpt}`);
      return lines.join("\n");
    })
    .join("\n");
}
