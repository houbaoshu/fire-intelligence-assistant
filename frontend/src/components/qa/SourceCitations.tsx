import { BookOpen } from "lucide-react";
import type { SourceCitation } from "@/lib/services/qa";
import { sourceMetaLine } from "./sourceText";

/**
 * 法规问答来源引用展示(specs/regulation-qa.md):
 * 只展示后端契约(API.md §5)确认返回的字段,逐项判空;
 * 不展示内部向量 ID 与相似度分数。
 */
export function SourceCitationList({ sources }: { sources: SourceCitation[] }) {
  return (
    <ul className="space-y-2">
      {sources.map((s, i) => {
        const meta = sourceMetaLine(s);
        return (
          <li
            key={`${s.document_id}-${i}`}
            className="rounded-md border border-border bg-muted/30 p-3 text-xs"
          >
            <div className="flex items-start gap-2">
              <BookOpen className="mt-0.5 h-3.5 w-3.5 shrink-0 text-muted-foreground" />
              <div className="min-w-0">
                <div className="font-medium text-foreground">{s.title}</div>
                {meta && <div className="mt-0.5 text-muted-foreground">{meta}</div>}
                {s.excerpt && (
                  <blockquote className="mt-1.5 border-l-2 border-border pl-2 leading-relaxed text-muted-foreground">
                    {s.excerpt}
                  </blockquote>
                )}
              </div>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
