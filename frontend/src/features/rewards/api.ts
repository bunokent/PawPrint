import { queryOptions, useMutation, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type RewardStatus = components["schemas"]["RewardStatus"];
export type RewardInit = components["schemas"]["RewardInit"];

export interface RewardCreateInput {
  flyer_id: string;
  provider: "stripe" | "gcash";
  amount_cents?: number;
  currency?: string;
}

export const rewardKeys = {
  status: (id: string) => ["rewards", "status", id] as const,
  mine: ["rewards", "mine"] as const,
};

export function useCreateReward() {
  return useMutation({
    mutationFn: (input: RewardCreateInput) => api.post<RewardInit>("/rewards", input).then((r) => r.data),
  });
}

export const rewardStatusQuery = (id: string) =>
  queryOptions({
    queryKey: rewardKeys.status(id),
    queryFn: async () => (await api.get<RewardStatus>(`/rewards/${id}/status`)).data,
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === undefined ? 2000 : false,
  });

/** Poll a reward transaction while it is pending; stops once terminal. */
export function useRewardStatus(id: string | undefined, enabled = true) {
  return useQuery({ ...rewardStatusQuery(id ?? "__none__"), enabled: enabled && Boolean(id) });
}

export const myRewardsQuery = () =>
  queryOptions({
    queryKey: rewardKeys.mine,
    queryFn: async () => (await api.get<RewardStatus[]>("/rewards/mine")).data,
  });
