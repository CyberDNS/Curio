import { ReactNode } from 'react'
import Header from './Header'
import Navigation from './Navigation'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <Navigation />
      <main className="flex-1 container mx-auto px-4 py-8 max-w-7xl">
        {children}
      </main>
      <footer className="border-t-4 border-newspaper-900 bg-newspaper-100 py-6 mt-12">
        <div className="container mx-auto px-4 text-center text-sm text-newspaper-600">
          <p className="font-serif">Curio - Your Personalized News Aggregator</p>
          <p className="mt-1">Powered by AI • Built with ❤️</p>
        </div>
      </footer>
    </div>
  )
}
