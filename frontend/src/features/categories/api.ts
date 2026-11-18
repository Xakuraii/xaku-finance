import { api } from "@/lib/api/client";

export interface CategoryItem {
  id: string;
  name: string;
  kind: "income" | "expense";
  parent_id?: string | null;
  children?: CategoryItem[];
}

export async function fetchCategories(): Promise<CategoryItem[]> {
  const data = await api.get<{ results?: CategoryItem[] } | CategoryItem[]>("/api/v1/categories/");
  if (Array.isArray(data)) return data;
  return data.results || [];
}
