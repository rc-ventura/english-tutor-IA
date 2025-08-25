import { describe, it, expect } from 'vitest';
import { __TEST_ONLY__ } from '../Chatbot';
import type { ChatMessage } from '../../types';

describe('getMessageText', () => {
  const fn = __TEST_ONLY__.getMessageText!;

  it('returns string content directly', () => {
    const msg: ChatMessage = { role: 'assistant', content: 'hello' };
    expect(fn(msg)).toBe('hello');
  });

  it('extracts text from nested content.text', () => {
    const msg: ChatMessage = { role: 'assistant', content: { text: 'hi' } as any };
    expect(fn(msg)).toBe('hi');
  });

  it('falls back to text_for_llm field', () => {
    const msg: ChatMessage = { role: 'assistant', content: null, text_for_llm: 'hey' };
    expect(fn(msg)).toBe('hey');
  });

  it('returns null when no text is present', () => {
    const msg: ChatMessage = { role: 'assistant', content: null };
    expect(fn(msg)).toBeNull();
  });
});
