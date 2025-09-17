'use client';

import { useSearch } from '@/hooks/useSearch';
import { Footer } from './Footer';

export function ConditionalFooter() {
  const { isInChatMode } = useSearch();
  
  // Don't render footer in chat mode to prevent overlap
  if (isInChatMode) {
    return null;
  }
  
  return <Footer />;
}
