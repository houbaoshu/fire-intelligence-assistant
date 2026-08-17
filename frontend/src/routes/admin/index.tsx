import { createFileRoute, redirect } from "@tanstack/react-router";

/** /admin 入口:重定向到组织管理页。 */
export const Route = createFileRoute("/admin/")({
  beforeLoad: () => {
    throw redirect({ to: "/admin/organizations" });
  },
});
