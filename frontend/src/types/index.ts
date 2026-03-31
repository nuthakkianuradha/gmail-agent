export interface User {
  id: string;
  email: string;
  name: string;
  picture_url: string | null;
}

export interface Email {
  id: string;
  gmail_message_id: string;
  gmail_thread_id: string;
  from_address: string;
  to_address: string;
  subject: string;
  body_text: string;
  body_html: string | null;
  snippet: string;
  labels: string[];
  received_at: string;
}

export interface EmailSummary {
  gmail_message_id: string;
  gmail_thread_id: string;
  from_address: string;
  to_address: string;
  subject: string;
  snippet: string;
  labels: string[];
  received_at: string | null;
  is_unread: boolean;
}

export interface InboxResponse {
  emails: EmailSummary[];
  next_page_token: string | null;
}

export interface ThreadResponse {
  thread_id: string;
  messages: Email[];
}

export interface EmailMessage {
  gmail_message_id: string;
  gmail_thread_id: string;
  from_address: string;
  to_address: string;
  subject: string;
  body_text: string;
  body_html: string | null;
  snippet: string;
  labels: string[];
  received_at: string | null;
}

export interface DraftRequest {
  gmail_message_id: string;
  gmail_thread_id: string;
}

export interface DraftResponse {
  draft: string;
  context_used: number;
}

export interface Persona {
  id?: string;
  display_name: string;
  tone: string;
  style_notes: string;
  signature: string;
  language: string;
  custom_instructions: string;
}

export interface Rule {
  id: string;
  rule_text: string;
  category: string;
  is_active: boolean;
  priority: number;
}
