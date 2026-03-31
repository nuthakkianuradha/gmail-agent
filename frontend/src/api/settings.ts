import client from './client';
import type { Persona, Rule } from '../types';

export async function fetchPersona(): Promise<Persona | null> {
  try {
    const { data } = await client.get('/settings/persona');
    return data;
  } catch {
    return null;
  }
}

export async function savePersona(persona: Persona): Promise<Persona> {
  const { data } = await client.put('/settings/persona', persona);
  return data;
}

export async function fetchRules(): Promise<Rule[]> {
  const { data } = await client.get('/settings/rules');
  return data;
}

export async function createRule(ruleText: string, category: string = 'general'): Promise<Rule> {
  const { data } = await client.post('/settings/rules', { rule_text: ruleText, category });
  return data;
}

export async function deleteRule(ruleId: string): Promise<void> {
  await client.delete(`/settings/rules/${ruleId}`);
}
