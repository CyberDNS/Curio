import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
  reorderCategories,
} from "../../services/api";
import { Plus, Trash2, Loader2, Pencil, GripVertical } from "lucide-react";
import type { CategoryCreate, Category } from "../../types";

export default function CategorySettings() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [editingCategory, setEditingCategory] = useState<Category | null>(null);
  const [newCategory, setNewCategory] = useState<CategoryCreate>({
    name: "",
    slug: "",
    description: "",
  });
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const { data: categories = [], isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: getCategories,
  });

  const createMutation = useMutation({
    mutationFn: createCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setNewCategory({ name: "", slug: "", description: "" });
      setShowForm(false);
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Category> }) =>
      updateCategory(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
      setEditingCategory(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteCategory,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const reorderMutation = useMutation({
    mutationFn: reorderCategories,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (newCategory.name && newCategory.slug) {
      createMutation.mutate(newCategory);
    }
  };

  const handleUpdate = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingCategory) {
      updateMutation.mutate({
        id: editingCategory.id,
        data: {
          name: editingCategory.name,
          slug: editingCategory.slug,
          description: editingCategory.description,
        },
      });
    }
  };

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)/g, "");
  };

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDragEnd = () => {
    if (
      draggedIndex !== null &&
      dragOverIndex !== null &&
      draggedIndex !== dragOverIndex
    ) {
      const newCategories = [...categories];
      const [draggedItem] = newCategories.splice(draggedIndex, 1);
      newCategories.splice(dragOverIndex, 0, draggedItem);

      // Update order in backend
      const categoryIds = newCategories.map((cat) => cat.id);
      reorderMutation.mutate(categoryIds);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  if (isLoading) {
    return <Loader2 className="w-6 h-6 animate-spin" />;
  }

  return (
    <div className="space-y-6">
      <h2 className="newspaper-heading text-2xl">Categories</h2>

      {/* Page Actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowForm(!showForm)}
          className="flex items-center gap-2 px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          Add Category
        </button>
      </div>

      {showForm && (
        <form
          onSubmit={handleSubmit}
          className="border border-newspaper-300 p-4 bg-newspaper-50"
        >
          <h3 className="font-semibold mb-4">Add New Category</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-1">Name *</label>
              <input
                type="text"
                value={newCategory.name}
                onChange={(e) => {
                  const name = e.target.value;
                  setNewCategory({
                    ...newCategory,
                    name,
                    slug: generateSlug(name),
                  });
                }}
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="Technology"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Slug *</label>
              <input
                type="text"
                value={newCategory.slug}
                onChange={(e) =>
                  setNewCategory({ ...newCategory, slug: e.target.value })
                }
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="technology"
                required
              />
              <p className="text-xs text-newspaper-600 mt-1">
                Used in URLs - lowercase, no spaces
              </p>
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">
                Description
              </label>
              <textarea
                value={newCategory.description}
                onChange={(e) =>
                  setNewCategory({
                    ...newCategory,
                    description: e.target.value,
                  })
                }
                className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                placeholder="Helps the AI classify articles into this category..."
                rows={3}
              />
              <p className="text-xs text-newspaper-600 mt-1">
                Describe what content belongs in this category. The AI uses this
                to classify articles.
              </p>
            </div>
            <div className="flex gap-2">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="px-4 py-2 bg-newspaper-900 text-white hover:bg-newspaper-700 transition-colors disabled:opacity-50"
              >
                {createMutation.isPending ? "Adding..." : "Add Category"}
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

      <div className="space-y-2">
        {categories.map((category, index) => (
          <div
            key={category.id}
            draggable={editingCategory?.id !== category.id}
            onDragStart={() => handleDragStart(index)}
            onDragOver={(e) => handleDragOver(e, index)}
            onDragEnd={handleDragEnd}
            onDragLeave={handleDragLeave}
            className={`transition-all ${
              dragOverIndex === index && draggedIndex !== index
                ? "border-t-4 border-blue-500"
                : ""
            } ${draggedIndex === index ? "opacity-50" : ""}`}
          >
            {editingCategory?.id === category.id ? (
              // Edit form
              <form
                onSubmit={handleUpdate}
                className="border border-newspaper-300 p-4 bg-newspaper-50"
              >
                <h3 className="font-semibold mb-4">Edit Category</h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Name *
                    </label>
                    <input
                      type="text"
                      value={editingCategory.name}
                      onChange={(e) => {
                        const name = e.target.value;
                        setEditingCategory({
                          ...editingCategory,
                          name,
                          slug: generateSlug(name),
                        });
                      }}
                      className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Slug *
                    </label>
                    <input
                      type="text"
                      value={editingCategory.slug}
                      onChange={(e) =>
                        setEditingCategory({
                          ...editingCategory,
                          slug: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                      required
                    />
                    <p className="text-xs text-newspaper-600 mt-1">
                      Used in URLs - lowercase, no spaces
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">
                      Description
                    </label>
                    <textarea
                      value={editingCategory.description || ""}
                      onChange={(e) =>
                        setEditingCategory({
                          ...editingCategory,
                          description: e.target.value,
                        })
                      }
                      className="w-full px-3 py-2 border border-newspaper-300 focus:outline-none focus:border-newspaper-900"
                      placeholder="Helps the AI classify articles into this category..."
                      rows={3}
                    />
                    <p className="text-xs text-newspaper-600 mt-1">
                      Describe what content belongs in this category. The AI
                      uses this to classify articles.
                    </p>
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
                      onClick={() => setEditingCategory(null)}
                      className="px-4 py-2 border border-newspaper-300 hover:bg-newspaper-100 transition-colors"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              </form>
            ) : (
              // Display mode
              <div className="flex items-start p-4 border border-newspaper-300 bg-white group">
                <button
                  className="cursor-grab active:cursor-grabbing p-2 -ml-2 text-newspaper-400 hover:text-newspaper-600 transition-colors"
                  title="Drag to reorder"
                >
                  <GripVertical className="w-5 h-5" />
                </button>
                <div className="flex-1">
                  <h4 className="font-semibold">{category.name}</h4>
                  <p className="text-sm text-newspaper-600">/{category.slug}</p>
                  {category.description && (
                    <p className="text-sm text-newspaper-700 mt-2 italic">
                      "{category.description}"
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setEditingCategory(category)}
                    className="p-2 text-newspaper-600 hover:bg-newspaper-100 rounded transition-colors"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete category "${category.name}"?`)) {
                        deleteMutation.mutate(category.id);
                      }
                    }}
                    disabled={deleteMutation.isPending}
                    className="p-2 text-red-600 hover:bg-red-50 rounded transition-colors disabled:opacity-50"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
        {categories.length === 0 && (
          <p className="text-center text-newspaper-600 py-8">
            No categories added yet. Click "Add Category" to organize your
            feeds!
          </p>
        )}
      </div>
    </div>
  );
}
