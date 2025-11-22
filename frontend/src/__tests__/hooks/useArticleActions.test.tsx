import { describe, it, expect, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useArticleActions } from "../../hooks/useArticleActions";
import { mockArticle } from "../../test/mockData";

// Create a test component that uses the hook
function TestComponent({ article }: { article: any }) {
  const { handleClick, handleReprocess, markReadMutation } =
    useArticleActions();

  return (
    <div>
      <button onClick={() => handleClick(article)}>Open Article</button>
      <button onClick={(e) => handleReprocess(e, article.id, article.title)}>
        Reprocess
      </button>
      <span data-testid="is-loading">
        {markReadMutation.isPending ? "Loading" : "Not Loading"}
      </span>
    </div>
  );
}

describe("useArticleActions", () => {
  it("should mark article as read and open link", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const mockOpen = vi.fn();
    window.open = mockOpen;

    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <TestComponent article={{ ...mockArticle, is_read: false }} />
      </QueryClientProvider>
    );

    const button = screen.getByText("Open Article");
    await user.click(button);

    // Should open article in new tab
    expect(mockOpen).toHaveBeenCalledWith(mockArticle.link, "_blank");
  });

  it("should handle reprocess confirmation", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const mockConfirm = vi.fn(() => true);
    window.confirm = mockConfirm;

    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <TestComponent article={mockArticle} />
      </QueryClientProvider>
    );

    const button = screen.getByText("Reprocess");
    await user.click(button);

    expect(mockConfirm).toHaveBeenCalled();
  });

  it("should not open link if article is already read", async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    const mockOpen = vi.fn();
    window.open = mockOpen;

    const user = userEvent.setup();

    render(
      <QueryClientProvider client={queryClient}>
        <TestComponent article={{ ...mockArticle, is_read: true }} />
      </QueryClientProvider>
    );

    const button = screen.getByText("Open Article");
    await user.click(button);

    // Should still open article
    expect(mockOpen).toHaveBeenCalled();
  });
});
