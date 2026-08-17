import { api } from "../api-client";
import type { Paginated } from "./common";
import type { UserRole } from "./auth";

/**
 * 企业管理后台服务:严格对齐 docs/API.md §11(Administration)。
 * 全部端点位于 /api/admin 前缀下,仅 admin 角色可访问;后端校验为权威,
 * 前端只负责展示后端返回的可读错误(409 归属冲突 / 自锁保护等)。
 */

/** 组织对象(API.md §11)。 */
export type AdminOrganization = {
  id: string;
  name: string;
  code: string;
  description: string | null;
  created_at: string;
  updated_at: string;
};

/** 新建组织请求体。 */
export type OrganizationCreateBody = {
  name: string;
  code: string;
  description?: string;
};

/** 更新组织请求体(字段可选,仅提交变更项)。 */
export type OrganizationUpdateBody = {
  name?: string;
  code?: string;
  description?: string;
};

/** 部门对象(API.md §11)。 */
export type AdminDepartment = {
  id: string;
  organization_id: string;
  name: string;
  parent_id: string | null;
  created_at: string;
  updated_at: string;
};

/** 新建部门请求体。 */
export type DepartmentCreateBody = {
  organization_id: string;
  name: string;
  parent_id?: string;
};

/** 更新部门请求体(所属组织不可变更)。 */
export type DepartmentUpdateBody = {
  name?: string;
  parent_id?: string | null;
};

/** 用户列表元素(API.md §11);username / 归属字段可为空。 */
export type AdminUser = {
  id: string;
  email: string;
  username: string | null;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  organization_id: string | null;
  department_id: string | null;
  last_login_at: string | null;
  created_at: string;
};

/** 更新用户请求体(角色 / 启用状态 / 组织与部门归属,字段可选)。 */
export type UserUpdateBody = {
  role?: UserRole;
  is_active?: boolean;
  organization_id?: string | null;
  department_id?: string | null;
};

/** 权限定义项。 */
export type AdminPermission = {
  code: string;
  name: string;
  description: string | null;
};

/** GET /api/admin/permissions 响应:权限清单 + 各角色已授予的权限码矩阵。 */
export type PermissionMatrix = {
  permissions: AdminPermission[];
  matrix: Partial<Record<UserRole, string[]>>;
};

/** PUT /api/admin/permissions/{role} 响应。 */
export type RolePermissions = {
  role: UserRole;
  permission_codes: string[];
};

/** 审计日志条目;details 为后端写入的 JSON 明细(结构随 action 而定)。 */
export type AdminAuditLog = {
  id: string;
  user_id: string | null;
  action: string;
  entity_type: string | null;
  entity_id: string | null;
  request_id: string | null;
  ip_address: string | null;
  details: Record<string, unknown> | null;
  created_at: string;
};

/** 删除响应信封(组织 / 部门共用)。 */
export type AdminDeleteResponse = {
  id: string;
  deleted: boolean;
};

export type OrganizationListParams = {
  page?: number;
  page_size?: number;
};

export type DepartmentListParams = {
  page?: number;
  page_size?: number;
  organization_id?: string;
};

export type UserListParams = {
  page?: number;
  page_size?: number;
  organization_id?: string;
  role?: UserRole;
};

export type AuditLogListParams = {
  page?: number;
  page_size?: number;
  user_id?: string;
  action?: string;
  entity_type?: string;
};

const base = "/api/admin";

export const adminService = {
  // ---- 组织 ----
  listOrganizations: (params: OrganizationListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<AdminOrganization>>(`${base}/organizations`, {
      query: { page: params.page, page_size: params.page_size },
      signal,
    }),
  createOrganization: (body: OrganizationCreateBody) =>
    api.post<AdminOrganization>(`${base}/organizations`, body),
  updateOrganization: (id: string, body: OrganizationUpdateBody) =>
    api.put<AdminOrganization>(`${base}/organizations/${encodeURIComponent(id)}`, body),
  /** 有用户归属时后端返回 409,前端原样展示其可读错误。 */
  deleteOrganization: (id: string) =>
    api.delete<AdminDeleteResponse>(`${base}/organizations/${encodeURIComponent(id)}`),

  // ---- 部门 ----
  listDepartments: (params: DepartmentListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<AdminDepartment>>(`${base}/departments`, {
      query: {
        page: params.page,
        page_size: params.page_size,
        organization_id: params.organization_id,
      },
      signal,
    }),
  createDepartment: (body: DepartmentCreateBody) =>
    api.post<AdminDepartment>(`${base}/departments`, body),
  updateDepartment: (id: string, body: DepartmentUpdateBody) =>
    api.put<AdminDepartment>(`${base}/departments/${encodeURIComponent(id)}`, body),
  deleteDepartment: (id: string) =>
    api.delete<AdminDeleteResponse>(`${base}/departments/${encodeURIComponent(id)}`),

  // ---- 用户 ----
  listUsers: (params: UserListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<AdminUser>>(`${base}/users`, {
      query: {
        page: params.page,
        page_size: params.page_size,
        organization_id: params.organization_id,
        role: params.role,
      },
      signal,
    }),
  /** 更新用户;自锁保护等冲突由后端返回 409 可读错误。 */
  updateUser: (id: string, body: UserUpdateBody) =>
    api.put<AdminUser>(`${base}/users/${encodeURIComponent(id)}`, body),

  // ---- 权限 ----
  getPermissions: (signal?: AbortSignal) =>
    api.get<PermissionMatrix>(`${base}/permissions`, { signal }),
  /** 覆盖式更新某角色的权限码集合;admin 的 admin.* 权限由后端拒绝变更。 */
  updateRolePermissions: (role: UserRole, permissionCodes: string[]) =>
    api.put<RolePermissions>(`${base}/permissions/${encodeURIComponent(role)}`, {
      permission_codes: permissionCodes,
    }),

  // ---- 审计日志 ----
  listAuditLogs: (params: AuditLogListParams = {}, signal?: AbortSignal) =>
    api.get<Paginated<AdminAuditLog>>(`${base}/audit-logs`, {
      query: {
        page: params.page,
        page_size: params.page_size,
        user_id: params.user_id,
        action: params.action,
        entity_type: params.entity_type,
      },
      signal,
    }),
};
