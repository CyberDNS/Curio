import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSetting, createOrUpdateSetting } from "../../services/api";
import { Save, Newspaper } from "lucide-react";

export default function AppSettings() {
  const queryClient = useQueryClient();
  const [newspaperTitle, setNewspaperTitle] = useState("");

  const { data: titleSetting } = useQuery({
    queryKey: ["settings", "newspaper_title"],
    queryFn: () => getSetting("newspaper_title"),
    retry: false,
  });

  useEffect(() => {
    if (titleSetting) {
      setNewspaperTitle(titleSetting.value);
    }
  }, [titleSetting]);

  const saveMutation = useMutation({
    mutationFn: (value: string) =>
      createOrUpdateSetting({ key: "newspaper_title", value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      alert("Settings saved successfully!");
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    saveMutation.mutate(newspaperTitle);
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="newspaper-heading text-2xl mb-2">Appearance Settings</h2>
        <p className="text-sm text-newspaper-600">
          Customize how your newspaper looks and feels
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Newspaper Title */}
        <div className="border border-newspaper-300 p-6 bg-white">
          <div className="flex items-center gap-2 mb-4">
            <Newspaper className="w-5 h-5" />
            <h3 className="font-semibold text-lg">Newspaper Title</h3>
          </div>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">
                Custom Title
              </label>
              <input
                type="text"
                value={newspaperTitle}
                onChange={(e) => setNewspaperTitle(e.target.value)}
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900 font-serif text-lg"
                placeholder="CURIO"
              />
              <p className="text-xs text-newspaper-600 mt-2">
                Leave empty to use default "CURIO". Your custom title will
                appear in the header.
              </p>
            </div>

            {/* Preview */}
            <div className="border-t border-newspaper-300 pt-4">
              <p className="text-xs font-semibold text-newspaper-600 mb-2">
                Preview:
              </p>
              <div className="border border-newspaper-300 p-4 bg-newspaper-50 text-center">
                <h1 className="newspaper-heading text-4xl tracking-tighter">
                  {newspaperTitle || "CURIO"}
                </h1>
                {newspaperTitle && (
                  <p className="text-xs text-newspaper-500 mt-1">by Curio</p>
                )}
                <p className="text-xs mt-1 text-newspaper-600 font-serif italic">
                  Your Personalized News Digest
                </p>
              </div>
            </div>
          </div>
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saveMutation.isPending ? "Saving..." : "Save Settings"}
          </button>

          {newspaperTitle && (
            <button
              type="button"
              onClick={() => setNewspaperTitle("")}
              className="px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors"
            >
              Reset to Default
            </button>
          )}
        </div>
      </form>
    </div>
  );
}
