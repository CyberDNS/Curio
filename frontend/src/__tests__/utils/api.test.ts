import { describe, it, expect } from "vitest";
import { getProxiedImageUrl } from "../../services/api";

describe("API utilities", () => {
  describe("getProxiedImageUrl", () => {
    it("should return null for null input", () => {
      expect(getProxiedImageUrl(null)).toBeNull();
    });

    it("should return null for undefined input", () => {
      expect(getProxiedImageUrl(undefined)).toBeNull();
    });

    it("should return local media path with API base URL", () => {
      const result = getProxiedImageUrl("/media/images/test.jpg");
      expect(result).toContain("/media/images/test.jpg");
    });

    it("should proxy external URLs", () => {
      const externalUrl = "https://example.com/image.jpg";
      const result = getProxiedImageUrl(externalUrl);
      expect(result).toContain("/proxy/image");
      expect(result).toContain(encodeURIComponent(externalUrl));
    });

    it("should handle legacy static paths", () => {
      const result = getProxiedImageUrl("/static/images/logo.png");
      expect(result).toContain("/static/images/logo.png");
    });
  });
});
