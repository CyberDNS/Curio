import { describe, it, expect } from "vitest";
import { renderHook } from "@testing-library/react";
import { useArticleFilters } from "../../hooks/useArticleFilters";
import { mockArticles } from "../../test/mockData";

describe("useArticleFilters", () => {
  it('should return all articles when filter is "all"', () => {
    const { result } = renderHook(() =>
      useArticleFilters({
        articles: mockArticles,
        statusFilter: "all",
      })
    );

    expect(result.current.filteredArticles.length).toBe(mockArticles.length);
  });

  it("should filter processed articles", () => {
    const { result } = renderHook(() =>
      useArticleFilters({
        articles: mockArticles,
        statusFilter: "processed",
      })
    );

    // All mock articles have summaries, so all are processed
    expect(result.current.filteredArticles.length).toBe(mockArticles.length);
  });

  it("should filter unprocessed articles", () => {
    const articlesWithUnprocessed = [
      ...mockArticles,
      {
        ...mockArticles[0],
        id: 99,
        summary: null,
      },
    ];

    const { result } = renderHook(() =>
      useArticleFilters({
        articles: articlesWithUnprocessed,
        statusFilter: "unprocessed",
      })
    );

    expect(result.current.filteredArticles.length).toBe(1);
    expect(result.current.filteredArticles[0].id).toBe(99);
  });

  it("should filter selected/recommended articles", () => {
    const { result } = renderHook(() =>
      useArticleFilters({
        articles: mockArticles,
        statusFilter: "selected",
      })
    );

    // Should only include articles with relevance_score >= 0.6
    const allSelected = result.current.filteredArticles.every(
      (a: any) => a.relevance_score >= 0.6
    );
    expect(allSelected).toBe(true);
  });

  it("should filter unselected articles", () => {
    const articlesWithLowScore = [
      ...mockArticles,
      {
        ...mockArticles[0],
        id: 98,
        relevance_score: 0.3,
      },
    ];

    const { result } = renderHook(() =>
      useArticleFilters({
        articles: articlesWithLowScore,
        statusFilter: "unselected",
      })
    );

    // Should only include articles with relevance_score < 0.6 and have summaries
    const allUnselected = result.current.filteredArticles.every(
      (a: any) => a.relevance_score < 0.6 && a.summary !== null
    );
    expect(allUnselected).toBe(true);
  });
});
