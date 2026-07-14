import { api } from "../api-client";

export type Capabilities = {
  application_version: string;
  environment: string;
  features: Record<string, boolean>;
  limits: { video_bytes: number; audio_bytes: number; document_bytes: number };
};

export const systemService = {
  capabilities: (signal?: AbortSignal) =>
    api.get<Capabilities>("/api/system/capabilities", { signal }),
};
