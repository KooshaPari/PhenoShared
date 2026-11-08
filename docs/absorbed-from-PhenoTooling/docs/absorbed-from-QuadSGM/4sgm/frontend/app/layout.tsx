import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { SessionProvider } from '@/components/session-provider'
import ChatWidget from '@/components/chat-widget'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: '4SGM - Four Seasons General Merchandise',
  description: 'Everything Your Store Needs Since 1984',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <SessionProvider>
          {children}
          {/* Global Chat Widget - Available on all pages */}
          <ChatWidget />
        </SessionProvider>
      </body>
    </html>
  )
}
