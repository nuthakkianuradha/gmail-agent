import client from './client';
import type { InboxResponse, ThreadResponse, EmailMessage } from '../types';

export async function fetchInbox(pageToken?: string): Promise<InboxResponse> {
  const params: Record<string, string> = {};
  if (pageToken) params.page_token = pageToken;
  const { data } = await client.get('/emails/inbox', { params });
  return data;
}

export async function fetchEmail(messageId: string): Promise<EmailMessage> {
  const { data } = await client.get(`/emails/${messageId}`);
  return data;
}

export async function fetchThread(threadId: string): Promise<ThreadResponse> {
  const { data } = await client.get(`/emails/thread/${threadId}`);
  return data;
}
