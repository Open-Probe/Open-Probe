import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Header } from '@/components/layout/Header';
import { ConditionalFooter } from '@/components/layout/ConditionalFooter';

const inter = Inter({ subsets: ['latin'] });

export const metadata: Metadata = {
  title: 'OpenProbe - AI-Powered Research Assistant',
  description: 'Ask complex questions and get detailed answers through intelligent web research and reasoning.',
  keywords: ['AI', 'search', 'research', 'assistant', 'web search', 'reasoning'],
  authors: [{ name: 'OpenProbe Team' }],
  viewport: 'width=device-width, initial-scale=1',
  robots: 'index, follow',
  openGraph: {
    title: 'OpenProbe - AI-Powered Research Assistant',
    description: 'Ask complex questions and get detailed answers through intelligent web research and reasoning.',
    type: 'website',
    locale: 'en_US',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'OpenProbe - AI-Powered Research Assistant',
    description: 'Ask complex questions and get detailed answers through intelligent web research and reasoning.',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head />
      <body className={`${inter.className} min-h-screen flex flex-col bg-background antialiased`}>
        <Header />
        <main className="flex-1 flex flex-col">
          {children}
        </main>
        <ConditionalFooter />
      </body>
    </html>
  );
}