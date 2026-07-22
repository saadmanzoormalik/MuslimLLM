export type ProviderCapability = {
  provider_id: string;
  display_name: string;
  available: boolean;
  button_label: "Connect" | "Coming soon";
  oauth_ready?: boolean;
  trust_label?: string;
  connection_method?: "broker_oauth" | "oauth" | "official_export" | "unavailable";
  compact_status?: string;
  integration_status?: "direct_sync" | "export_sync" | "limited_sync" | "unavailable" | "coming_soon";
  capabilities?: Record<string, string>;
};

export type SyncJob = {
  id: string;
  provider_id: string;
  status: string;
  stage: string;
  processed: number;
  total: number;
  percent: number;
  estimated_seconds_remaining?: number | null;
  display_message?: string;
  ready_for_use?: boolean;
  entry_chat_id?: string | null;
};

export type ConnectionResult = {
  connection_id: string;
  provider_id: string;
  next_action: "redirect" | "sync" | "unavailable";
  authorization_url?: string | null;
  job_id?: string | null;
  user_message?: string | null;
};

export type ModelConnection = {
  id: string;
  status: "active" | "connected" | "disconnected";
  mode: "local" | "remote";
  endpoint: string;
  model: string;
  last_checked_at?: string | null;
};
