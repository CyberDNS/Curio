import { describe, it, expect, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import FeedSettings from "../../components/Settings/FeedSettings";
import * as api from "../../services/api";

// Mock the API module
vi.mock("../../services/api", () => ({
  getFeeds: vi.fn(),
  createFeed: vi.fn(),
  updateFeed: vi.fn(),
  deleteFeed: vi.fn(),
  fetchFeeds: vi.fn(),
}));

describe("FeedSettings", () => {
  let queryClient: QueryClient;

  const mockFeeds = [
    {
      id: 1,
      url: "https://example.com/feed1.xml",
      title: "Test Feed 1",
      source_title: "Test Source 1",
      description: "Test description 1",
      is_active: true,
      fetch_interval: 60,
      last_fetched: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
    {
      id: 2,
      url: "https://example.com/feed2.xml",
      title: "Test Feed 2",
      source_title: "Test Source 2",
      description: "Test description 2",
      is_active: true,
      fetch_interval: 60,
      last_fetched: null,
      created_at: "2024-01-01T00:00:00Z",
      updated_at: "2024-01-01T00:00:00Z",
    },
  ];

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const renderComponent = () => {
    return render(
      <QueryClientProvider client={queryClient}>
        <FeedSettings />
      </QueryClientProvider>
    );
  };

  describe("Feed Deletion", () => {
    it("should successfully delete a feed when user confirms", async () => {
      // Setup
      vi.mocked(api.getFeeds).mockResolvedValue(mockFeeds);
      vi.mocked(api.deleteFeed).mockResolvedValue(undefined);

      // Mock window.confirm to return true
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      const user = userEvent.setup();

      // Render
      renderComponent();

      // Wait for feeds to load
      await waitFor(() => {
        expect(screen.getByText("Test Feed 1")).toBeInTheDocument();
      });

      // Find and click delete button for the first feed
      const deleteButtons = screen.getAllByTitle("Delete feed");
      expect(deleteButtons.length).toBe(2);

      await user.click(deleteButtons[0]);

      // Verify confirmation dialog was shown
      expect(confirmSpy).toHaveBeenCalledWith('Delete feed "Test Feed 1"?');

      // Verify deleteFeed was called with correct ID
      await waitFor(() => {
        expect(api.deleteFeed).toHaveBeenCalled();
        const callArgs = vi.mocked(api.deleteFeed).mock.calls[0];
        expect(callArgs[0]).toBe(1);
      });

      confirmSpy.mockRestore();
    });

    it("should not delete feed when user cancels confirmation", async () => {
      // Setup
      vi.mocked(api.getFeeds).mockResolvedValue(mockFeeds);
      vi.mocked(api.deleteFeed).mockResolvedValue(undefined);

      // Mock window.confirm to return false
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);

      const user = userEvent.setup();

      // Render
      renderComponent();

      // Wait for feeds to load
      await waitFor(() => {
        expect(screen.getByText("Test Feed 1")).toBeInTheDocument();
      });

      // Find and click delete button
      const deleteButtons = screen.getAllByTitle("Delete feed");
      await user.click(deleteButtons[0]);

      // Verify confirmation was shown
      expect(confirmSpy).toHaveBeenCalled();

      // Verify deleteFeed was NOT called
      expect(api.deleteFeed).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });

    it("should handle feed deletion errors gracefully", async () => {
      // Setup
      vi.mocked(api.getFeeds).mockResolvedValue(mockFeeds);
      vi.mocked(api.deleteFeed).mockRejectedValue(
        new Error("Failed to delete feed")
      );

      // Mock window.confirm to return true
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      // Mock console.error to suppress error output in test
      const consoleErrorSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      const user = userEvent.setup();

      // Render
      renderComponent();

      // Wait for feeds to load
      await waitFor(() => {
        expect(screen.getByText("Test Feed 1")).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByTitle("Delete feed");
      await user.click(deleteButtons[0]);

      // Verify deleteFeed was called
      await waitFor(() => {
        expect(api.deleteFeed).toHaveBeenCalled();
        const callArgs = vi.mocked(api.deleteFeed).mock.calls[0];
        expect(callArgs[0]).toBe(1);
      });

      // Feed should still be visible since deletion failed
      expect(screen.getByText("Test Feed 1")).toBeInTheDocument();

      confirmSpy.mockRestore();
      consoleErrorSpy.mockRestore();
    });

    it("should disable delete button while deletion is in progress", async () => {
      // Setup - make deleteFeed take some time
      let resolveDelete: () => void;
      const deletePromise = new Promise<void>((resolve) => {
        resolveDelete = resolve;
      });

      vi.mocked(api.getFeeds).mockResolvedValue(mockFeeds);
      vi.mocked(api.deleteFeed).mockReturnValue(deletePromise);

      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(true);

      const user = userEvent.setup();

      // Render
      renderComponent();

      // Wait for feeds to load
      await waitFor(() => {
        expect(screen.getByText("Test Feed 1")).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByTitle("Delete feed");
      await user.click(deleteButtons[0]);

      // Button should be disabled while deletion is in progress
      await waitFor(() => {
        expect(deleteButtons[0]).toBeDisabled();
      });

      // Resolve the deletion
      resolveDelete!();

      await waitFor(() => {
        expect(api.deleteFeed).toHaveBeenCalled();
      });

      confirmSpy.mockRestore();
    });
  });
});
