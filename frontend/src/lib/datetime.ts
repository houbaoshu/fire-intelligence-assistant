/** ISO 8601 时间戳与本地 datetime-local 输入值之间的转换与展示格式化。 */

/** ISO 时间戳 → 展示文本;空值返回占位符,非法值按「不可用」处理返回 null。 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "不可用";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** ISO 时间戳 → datetime-local 输入值(本地时区);空值返回空串。 */
export function toLocalInputValue(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

/** datetime-local 输入值 → ISO 8601 UTC;空值返回 null,非法输入返回 undefined(调用方应校验)。 */
export function fromLocalInputValue(value: string): string | null | undefined {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}
