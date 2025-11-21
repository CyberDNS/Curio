import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getFeeds,
  createFeed,
  updateFeed,
  deleteFeed,
  fetchFeeds,
} from "../../services/api";
import {
  Plus,
  Trash2,
  Loader2,
  RefreshCw,
  Pencil,
} from "lucide-react";
import type { FeedCreate, Feed } from "../../types";

export default function FeedSettings() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingFeed, setEditingFeed] = useState<Feed | null>(null);
  const [newFeed, setNewFeed] = useState<FeedCreate>({ url: "" });
  const [showFetchDialog, setShowFetchDialog] = useState(false);
  const [fetchingFeedId, setFetchingFeedId] = useState<number | null>(null);
  const [daysBack, setDaysBack] = useState<number>(7);
  const [fetchingFeeds, setFetchingFeeds] = useState<Set<number>>(new Set());

  const { data: feeds = [], isLoading } = useQuery({
    queryKey: ["feeds"],
    queryFn: getFeeds,
  });

  const createMutation = useMutation({
    mutationFn: createFeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feeds"] });
      setNewFeed({ url: "" });
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Feed> }) =>
      updateFeed(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feeds"] });
      setEditingFeed(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteFeed,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["feeds"] });
    },
  });

  const fetchMutation = useMutation({
    mutationFn: ({ feedId, days }: { feedId?: number; days: number }) =>
      fetchFeeds(feedId, days),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["articles"] });
      setFetchingFeeds((prev) => {
        const next = new Set(prev);
        if (variables.feedId) {
          next.delete(variables.feedId);
        } else {
          next.clear();
        }
        return next;
      });
      setShowFetchDialog(false);
      setFetchingFeedId(null);
    },
    onError: (_, variables) => {
      setFetchingFeeds((prev) => {
        const next = new Set(prev);
        if (variables.feedId) {
          next.delete(variables.feedId);
        } else {
          next.clear();
        }
        return next;
      });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newFeed.url) {
      createMutation.mutate(newFeed);
    }
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingFeed) {
      updateMutation.mutate({
        id: editingFeed.id,
        data: {
          url: editingFeed.url,
          title: editingFeed.title,
          source_title: editingFeed.source_title,
          description: editingFeed.description,
          is_active: editingFeed.is_active,
          fetch_interval: editingFeed.fetch_interval,
        },
      });
    }
  };

  const handleFetchClick = (feedId?: number) => {
    setFetchingFeedId(feedId || null);
    setShowFetchDialog(true);
  };

  const handleFetchConfirm = () => {
    if (fetchingFeedId) {
      setFetchingFeeds((prev) => new Set(prev).add(fetchingFeedId));
    } else {
      // Fetching all feeds - mark all as fetching
      setFetchingFeeds(new Set(feeds.map((f) => f.id)));
    }
    fetchMutation.mutate({
      feedId: fetchingFeedId || undefined,
      days: daysBack,
    });
  };

  if (isLoading) {
    return <Loader2 className="w-6 h-6 animate-spin" />;
  }

  return (
    <div className="space-y-6">
      <h2 className="newspaper-heading text-2xl">RSS Feeds</h2>

      {/* Page Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Feed
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="border border-newspaper-300 p-4 bg-newspaper-50"
        >
          <h3 className="font-semibold mb-4">Add New RSS Feed</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">
                Feed URL *
              </label>
              <input
                type="url"
                value={newFeed.url}
                onChange={(e) =>
                  setNewFeed({ ...newFeed, url: e.target.value })
                }
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="https://example.com/feed.xml"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Source Title
              </label>
              <input
                type="text"
                value={newFeed.source_title || ""}
                onChange={(e) =>
                  setNewFeed({ ...newFeed, source_title: e.target.value })
                }
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="New York Times"
              />
              <p className="text-xs text-newspaper-600 mt-1">
                Display name for this source (shown in newspaper)
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors disabled:opacity-50"
              >
                {createMutation.isPending ? "Adding..." : "Add Feed"}
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        </form>
      )}

      {/* Fetch Dialog */}
      {showFetchDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 max-w-md w-full mx-4 border-2 border-newspaper-900">
            <h3 className="newspaper-heading text-xl mb-4">
              {fetchingFeedId ? "Fetch Feed" : "Fetch All Feeds"}
            </h3>
            <p className="text-sm text-newspaper-600 mb-4">
              {fetchingFeedId
                ? `Fetch articles from "${
                    feeds.find((f) => f.id === fetchingFeedId)?.title ||
                    "this feed"
                  }"`
                : "Fetch articles from all RSS feeds"}
            </p>
            <div className="mb-6">
              <label className="block text-sm font-medium mb-2">
                Days to go back
              </label>
              <input
                type="number"
                min="1"
                max="365"
                value={daysBack}
                onChange={(e) => setDaysBack(parseInt(e.target.value) || 7)}
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="7"
              />
              <p className="text-xs text-newspaper-600 mt-1">
                Note: Most RSS feeds only provide recent articles (typically
                10-50 items)
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleFetchConfirm}
                disabled={fetchMutation.isPending}
                className="flex-1 px-4 py-2 bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50"
              >
                {fetchMutation.isPending ? "Fetching..." : "Fetch"}
              </button>
              <button
                onClick={() => {
                  setShowFetchDialog(false);
                  setFetchingFeedId(null);
                }}
                disabled={fetchMutation.isPending}
                className="flex-1 px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors disabled:opacity-50"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {feeds.map((feed) => (
          <div key={feed.id}>
            {editingFeed?.id === feed.id ? (
              // Edit form
              <form
                onSubmit={handleUpdate}
                className="border border-newspaper-300 p-4 bg-newspaper-50"
              >
                <h3 className="font-semibold mb-4">Edit Feed</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Feed URL *
                    </label>
                    <input
                      type="url"
                      value={editingFeed.url}
                      onChange={(e) =>
                        setEditingFeed({ ...editingFeed, url: e.target.value })
                      }
                      className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Source Title
                    </label>
                    <input
                      type="text"
                      value={editingFeed.source_title || ""}
                      onChange={(e) =>
                        setEditingFeed({
                          ...editingFeed,
                          source_title: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                      placeholder="New York Times"
                    />
                    <p className="text-xs text-newspaper-600 mt-1">
                      Display name for this source (shown in newspaper)
                    </p>
                  </div>
                  <div>
                    <label className="flex items-center gap-2">
                      <input
                        type="checkbox"
                        checked={editingFeed.is_active}
                        onChange={(e) =>
                          setEditingFeed({
                            ...editingFeed,
                            is_active: e.target.checked,
                          })
                        }
                        className="w-4 h-4"
                      />
                      <span className="text-sm font-medium">Active</span>
                    </label>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="submit"
                      disabled={updateMutation.isPending}
                      className="px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors disabled:opacity-50"
                    >
                      {updateMutation.isPending ? "Saving..." : "Save Changes"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditingFeed(null)}
                      className="px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              // Display mode
              <div className="flex justify-between items-center p-4 border border-newspaper-300 bg-white">
                <div className="flex-1">
                  <h4 className="font-semibold">
                    {feed.title || "Untitled Feed"}
                  </h4>
                  {feed.source_title && (
                    <p className="text-sm text-newspaper-700 italic">
                      Source: {feed.source_title}
                    </p>
                  )}
                  <p className="text-sm text-newspaper-600 truncate">
                    {feed.url}
                  </p>
                  {feed.last_fetched && (
                    <p className="text-xs text-newspaper-500 mt-1">
                      Last fetched:{" "}
                      {new Date(feed.last_fetched).toLocaleString()}
                    </p>
                  )}
                  {!feed.is_active && (
                    <span className="inline-block px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded mt-1">
                      Inactive
                    </span>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingFeed(feed)}
                    className="p-2 text-newspaper-600 hover:bg-newspaper-100 rounded transition-colors"
                    title="Edit feed"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleFetchClick(feed.id)}
                    disabled={fetchingFeeds.has(feed.id)}
                    className="p-2 text-newspaper-600 hover:bg-newspaper-100 rounded transition-colors disabled:opacity-50"
                    title="Fetch this feed"
                  >
                    <RefreshCw
                      className={`w-4 h-4 ${
                        fetchingFeeds.has(feed.id) ? "animate-spin" : ""
                      }`}
                    />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete feed "${feed.title || feed.url}"?`)) {
                        deleteMutation.mutate(feed.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                    className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                    title="Delete feed"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {feeds.length === 0 && (
          <p className="text-center text-newspaper-600 py-8">
            No feeds added yet. Click "Add Feed" to get started!
          </p>
        )}
      </div>
    </div>
  );
}
