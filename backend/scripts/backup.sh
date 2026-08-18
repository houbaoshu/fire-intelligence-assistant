#!/usr/bin/env bash
# Fire Intelligence Platform 备份脚本（M7）
#
# 用法：./scripts/backup.sh <输出目录>
#
# 输出带时间戳的子目录 backup-YYYYmmdd-HHMMSS，包含：
#   - db.sqlite3          SQLite 快照（DATABASE_URL 为 SQLite 时）
#   - db.dump             PostgreSQL pg_dump 自定义格式归档（DATABASE_URL 为 PG 时）
#   - storage.tar.gz      对象存储目录归档（STORAGE_PROVIDER=local）
#   - vectorstore.tar.gz  本地向量库快照（VECTOR_STORE_PROVIDER=local）
#
# 配置来源：环境变量优先，其次 backend/.env。
# PostgreSQL 环境优先使用 pg_dump；pg_dump 不存在时给出可读报错并非零退出。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ $# -ne 1 ]]; then
  echo "用法: $0 <输出目录>" >&2
  exit 2
fi
OUT_DIR="$1"
mkdir -p "${OUT_DIR}"

# 从 backend/.env 读取未在环境中设置的变量（忽略注释与空行）
load_env() {
  local name="$1"
  if [[ -n "${!name:-}" ]]; then
    return
  fi
  local env_file="${BACKEND_DIR}/.env"
  if [[ -f "${env_file}" ]]; then
    local value
    value="$(grep -E "^${name}=" "${env_file}" | tail -n1 | cut -d= -f2- || true)"
    if [[ -n "${value}" ]]; then
      export "${name}=${value}"
    fi
  fi
}
load_env DATABASE_URL
load_env STORAGE_DIR
load_env VECTOR_STORE_DIR
load_env VECTOR_STORE_PROVIDER

DATABASE_URL="${DATABASE_URL:-sqlite:///./data/app.db}"
STORAGE_DIR="${STORAGE_DIR:-./data/storage}"
VECTOR_STORE_DIR="${VECTOR_STORE_DIR:-./data/vectorstore}"
VECTOR_STORE_PROVIDER="${VECTOR_STORE_PROVIDER:-local}"

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="${OUT_DIR}/backup-${TIMESTAMP}"
mkdir -p "${BACKUP_DIR}"
echo "备份输出目录: ${BACKUP_DIR}"

# 相对路径一律相对 backend 根目录解析
resolve_path() {
  local p="$1"
  if [[ "${p}" = /* ]]; then
    echo "${p}"
  else
    echo "${BACKEND_DIR}/${p}"
  fi
}

# ---- 数据库 ----
if [[ "${DATABASE_URL}" = sqlite:///* ]]; then
  DB_PATH="$(resolve_path "${DATABASE_URL#sqlite:///}")"
  if [[ ! -f "${DB_PATH}" ]]; then
    echo "错误: SQLite 数据库文件不存在: ${DB_PATH}" >&2
    exit 1
  fi
  if command -v sqlite3 >/dev/null 2>&1; then
    # 在线一致性快照（无需停服）
    sqlite3 "${DB_PATH}" ".backup '${BACKUP_DIR}/db.sqlite3'"
  else
    echo "警告: 未找到 sqlite3，退化为文件拷贝（请在低峰期执行）" >&2
    cp "${DB_PATH}" "${BACKUP_DIR}/db.sqlite3"
  fi
  echo "SQLite 快照完成: ${BACKUP_DIR}/db.sqlite3"
elif [[ "${DATABASE_URL}" = postgresql* ]]; then
  if ! command -v pg_dump >/dev/null 2>&1; then
    echo "错误: DATABASE_URL 为 PostgreSQL，但未找到 pg_dump。" >&2
    echo "请安装 PostgreSQL 客户端工具（如 apt install postgresql-client）后重试。" >&2
    exit 1
  fi
  # pg_dump 接受标准连接串；去掉 SQLAlchemy 驱动前缀（postgresql+psycopg:// → postgresql://）
  PG_URL="${DATABASE_URL/postgresql+*:\/\//postgresql://}"
  pg_dump --format=custom --file="${BACKUP_DIR}/db.dump" "${PG_URL}"
  echo "PostgreSQL 备份完成: ${BACKUP_DIR}/db.dump"
else
  echo "错误: 无法识别的 DATABASE_URL: ${DATABASE_URL}" >&2
  exit 1
fi

# ---- 对象存储（local provider） ----
STORAGE_PATH="$(resolve_path "${STORAGE_DIR}")"
if [[ -d "${STORAGE_PATH}" ]]; then
  tar -czf "${BACKUP_DIR}/storage.tar.gz" -C "${STORAGE_PATH}" .
  echo "存储归档完成: ${BACKUP_DIR}/storage.tar.gz"
else
  echo "提示: 存储目录不存在，跳过: ${STORAGE_PATH}" >&2
fi

# ---- 本地向量库 ----
if [[ "${VECTOR_STORE_PROVIDER}" = "local" ]]; then
  VECTOR_PATH="$(resolve_path "${VECTOR_STORE_DIR}")"
  if [[ -d "${VECTOR_PATH}" ]]; then
    tar -czf "${BACKUP_DIR}/vectorstore.tar.gz" -C "${VECTOR_PATH}" .
    echo "向量库快照完成: ${BACKUP_DIR}/vectorstore.tar.gz"
  else
    echo "提示: 向量库目录不存在，跳过: ${VECTOR_PATH}" >&2
  fi
fi

echo "备份完成: ${BACKUP_DIR}"
