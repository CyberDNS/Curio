import { useState, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { getSetting, createOrUpdateSetting } from "../../services/api";
import { Save } from "lucide-react";

export default function LLMSettings() {
  const queryClient = useQueryClient();
  const [prompt, setPrompt] = useState("");

  const { data: promptSetting } = useQuery({
    queryKey: ["settings", "llm_selection_prompt"],
    queryFn: () => getSetting("llm_selection_prompt"),
    retry: false,
  });

  useEffect(() => {
    if (promptSetting) {
      setPrompt(promptSetting.value);
    }
  }, [promptSetting]);

  const saveMutation = useMutation({
    mutationFn: (value: string) =>
      createOrUpdateSetting({ key: "llm_selection_prompt", value }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings"] });
      alert("Settings saved successfully!");
    },
  });

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    saveMutation.mutate(prompt);
  };

  const defaultPrompt = `I'm interested in:
- Technology and innovation
- Science discoveries
- Business and startups
- AI and machine learning

Please select articles that match these interests and provide concise summaries.`;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="newspaper-heading text-2xl mb-2">AI Content Curation</h2>
        <p className="text-sm text-newspaper-600">
          Define your interests and preferences. The AI will use this to select
          and summarize relevant articles.
        </p>
      </div>

      <form onSubmit={handleSave} className="space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2">
            Your Interests & Preferences
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900 font-mono text-sm"
            rows={12}
            placeholder={defaultPrompt}
          />
          <p className="text-xs text-newspaper-600 mt-2">
            Describe what topics, themes, or types of content you're interested
            in. Be specific for better results.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="flex items-center gap-2 px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors disabled:opacity-50"
          >
            <Save className="w-4 h-4" />
            {saveMutation.isPending ? "Saving..." : "Save Preferences"}
          </button>

          {prompt && (
            <button
              type="button"
              onClick={() => setPrompt(defaultPrompt)}
              className="px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors"
            >
              Reset to Default
            </button>
          )}
        </div>
      </form>

      <div className="border border-yellow-200 bg-yellow-50 p-4">
        <h4 className="font-semibold text-yellow-900 mb-2">Note</h4>
        <p className="text-sm text-yellow-800">
          AI processing uses OpenAI's API. Make sure you have configured your
          API key in the backend environment variables. Processing large numbers
          of articles may incur API costs.
        </p>
      </div>
    </div>
  );
}
