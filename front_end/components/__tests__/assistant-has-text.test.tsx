import { describe, it, expect } from 'vitest';
import { __TEST_ONLY__ } from '../SpeakingTab';
import type { ChatMessage } from '../../types';

describe('assistantHasText', () => {
  const fn = __TEST_ONLY__.assistantHasText!;

  it('detects plain string content', () => {
    const msgs: ChatMessage[] = [{ role: 'assistant', content: 'hello' }];
    expect(fn(msgs)).toBe(true);
  });

  it('detects text inside content.text', () => {
    const msgs: ChatMessage[] = [{ role: 'assistant', content: { text: 'hi' } as any }];
    expect(fn(msgs)).toBe(true);
  });

  it('detects text_for_llm field', () => {
    const msgs: ChatMessage[] = [{ role: 'assistant', content: null, text_for_llm: 'hey' }];
    expect(fn(msgs)).toBe(true);
  });

  it('returns false when no text is present', () => {
    const msgs: ChatMessage[] = [{ role: 'assistant', content: null }];
    expect(fn(msgs)).toBe(false);
  });
});
