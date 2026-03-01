import { createClient } from "@supabase/supabase-js";

declare global {
  interface Window {
    __FATIMA_ENV__?: {
      VITE_SUPABASE_URL?: string;
      VITE_SUPABASE_ANON_KEY?: string;
    };
  }
}

const runtimeUrl = window.__FATIMA_ENV__?.VITE_SUPABASE_URL;
const runtimeKey = window.__FATIMA_ENV__?.VITE_SUPABASE_ANON_KEY;

const supabaseUrl =
  (runtimeUrl && runtimeUrl.length > 0 ? runtimeUrl : undefined) ??
  (import.meta.env.VITE_SUPABASE_URL as string);
const supabaseAnonKey =
  (runtimeKey && runtimeKey.length > 0 ? runtimeKey : undefined) ??
  (import.meta.env.VITE_SUPABASE_ANON_KEY as string);

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
