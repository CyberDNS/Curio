import { useState } from 'react'
import FeedSettings from '../components/Settings/FeedSettings'
import CategorySettings from '../components/Settings/CategorySettings'
import LLMSettings from '../components/Settings/LLMSettings'
import AppSettings from '../components/Settings/AppSettings'
import PageHeader from '../components/Layout/PageHeader'

type Tab = 'feeds' | 'categories' | 'llm' | 'app'

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState<Tab>('feeds')

  return (
    <div>
      <PageHeader
        title="Settings"
        subtitle="Configure your RSS feeds, categories, and AI preferences"
      />

      {/* Tabs */}
      <div className="border-b border-newspaper-300 mb-6">
        <div className="flex gap-4 overflow-x-auto">
          <button
            onClick={() => setActiveTab('feeds')}
            className={`px-4 py-2 font-semibold transition-colors border-b-2 whitespace-nowrap ${
              activeTab === 'feeds'
                ? 'border-newspaper-900 text-newspaper-900'
                : 'border-transparent text-newspaper-600 hover:text-newspaper-900'
            }`}
          >
            RSS Feeds
          </button>
          <button
            onClick={() => setActiveTab('categories')}
            className={`px-4 py-2 font-semibold transition-colors border-b-2 whitespace-nowrap ${
              activeTab === 'categories'
                ? 'border-newspaper-900 text-newspaper-900'
                : 'border-transparent text-newspaper-600 hover:text-newspaper-900'
            }`}
          >
            Categories
          </button>
          <button
            onClick={() => setActiveTab('llm')}
            className={`px-4 py-2 font-semibold transition-colors border-b-2 whitespace-nowrap ${
              activeTab === 'llm'
                ? 'border-newspaper-900 text-newspaper-900'
                : 'border-transparent text-newspaper-600 hover:text-newspaper-900'
            }`}
          >
            AI Settings
          </button>
          <button
            onClick={() => setActiveTab('app')}
            className={`px-4 py-2 font-semibold transition-colors border-b-2 whitespace-nowrap ${
              activeTab === 'app'
                ? 'border-newspaper-900 text-newspaper-900'
                : 'border-transparent text-newspaper-600 hover:text-newspaper-900'
            }`}
          >
            Appearance
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div>
        {activeTab === 'feeds' && <FeedSettings />}
        {activeTab === 'categories' && <CategorySettings />}
        {activeTab === 'llm' && <LLMSettings />}
        {activeTab === 'app' && <AppSettings />}
      </div>
    </div>
  )
}
