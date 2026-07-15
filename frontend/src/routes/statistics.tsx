import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { ErrorState, LoadingState } from "@/components/common/StateViews";
import { PageHeader } from "@/components/layout/AppShell";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { statisticsService } from "@/lib/services/statistics";

export const Route = createFileRoute("/statistics")({
  head: () => ({ meta: [{ title: "统计 · 消防智能助手" }] }),
  component: StatisticsPage,
});

function StatisticsPage() {
  const query = useQuery({
    queryKey: ["statistics"],
    queryFn: ({ signal }) => statisticsService.get(signal),
  });
  return (
    <div className="mx-auto max-w-6xl">
      <PageHeader
        title="统计"
        description="所有数值均来自后端授权范围；零、不可用和错误不会混为一谈。"
      />
      {query.isLoading ? (
        <LoadingState title="正在汇总统计" />
      ) : query.error ? (
        <ErrorState description={query.error.message} onRetry={() => query.refetch()} />
      ) : (
        query.data && (
          <>
            <div className="mb-4 text-xs text-muted-foreground">
              范围：{query.data.scope} · 时区：{query.data.timezone} · 更新：
              {new Date(query.data.last_updated_at).toLocaleString()}
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {query.data.metrics.map((metric) => (
                <Card key={metric.id}>
                  <CardContent className="p-5">
                    <div className="text-sm text-muted-foreground">{metric.label}</div>
                    <div className="mt-2 text-3xl font-semibold">
                      {metric.available && metric.value !== null
                        ? `${metric.value} ${metric.unit}`
                        : "不可用"}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
            <div className="mt-6 grid gap-4 lg:grid-cols-2">
              <StatusTable title="任务状态" values={query.data.task_statuses} />
              <StatusTable title="知识索引状态" values={query.data.knowledge_statuses} />
            </div>
          </>
        )
      )}
    </div>
  );
}

function StatusTable({ title, values }: { title: string; values: Record<string, number> }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm">{title}</CardTitle>
      </CardHeader>
      <CardContent>
        {Object.keys(values).length === 0 ? (
          <p className="text-sm text-muted-foreground">当前范围暂无数据。</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left">
                <th className="py-2">状态</th>
                <th className="py-2 text-right">数量</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(values).map(([status, count]) => (
                <tr key={status} className="border-b last:border-0">
                  <td className="py-2">{status}</td>
                  <td className="py-2 text-right">{count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </CardContent>
    </Card>
  );
}
