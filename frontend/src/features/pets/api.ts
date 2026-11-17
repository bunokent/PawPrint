import { useMutation } from "@tanstack/react-query";
import { api, multipartConfig } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type Pet = components["schemas"]["Pet"];

export interface PhotoUploadResult {
  key: string;
  url: string;
  thumb_key: string;
  thumb_url: string;
  pet_classes: string[];
  detected_classes: string[];
  max_confidence: number;
}

export interface PetCreateInput {
  name: string;
  species: string;
  breed?: string;
  color?: string;
  age?: number | null;
  temperament_tags?: string[];
  health_tags?: string[];
  photo_path?: string;
  status?: string;
}

export function useUploadPetPhoto() {
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("photo", file);
      const { data } = await api.post<PhotoUploadResult>("/pets/photos", form, multipartConfig());
      return data;
    },
  });
}

export function useCreatePet() {
  return useMutation({
    mutationFn: (input: PetCreateInput) => api.post<Pet>("/pets", input).then((r) => r.data),
  });
}
