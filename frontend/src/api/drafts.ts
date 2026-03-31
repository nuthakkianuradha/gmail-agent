import client from './client';
import type { DraftResponse } from '../types';

export async function generateDraft(
  gmailMessageId: string,
  gmailThreadId: string
): Promise<DraftResponse> {
  const { data } = await client.post('/drafts/generate', {
    gmail_message_id: gmailMessageId,
    gmail_thread_id: gmailThreadId,
  });
  return data;
}

export async function sendDraft(payload: {
  gmail_thread_id: string;
  gmail_message_id: string;
  to: string;
  subject: string;
  body: string;
  draft_before?: string;
}): Promise<{ status: string }> {
  const { data } = await client.post('/drafts/send', payload);
  return data;
}
