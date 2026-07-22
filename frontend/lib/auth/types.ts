export type AuthUser = {
  authenticated: true;
  account_type: "user" | "guest";
  email?: string | null;
  display_name?: string | null;
  identities?: Array<{ provider: string; provider_email?: string; provider_email_verified?: boolean }>;
  onboarding?: {
    primary_use?: string;
    response_preference?: string;
    privacy_preference?: string;
    context_transfer_preference?: string;
    completed?: boolean;
  } | null;
};
