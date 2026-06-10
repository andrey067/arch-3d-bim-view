export interface CurrentUser {
  id: string;
  email: string;
}

const FIXED_USER: CurrentUser = {
  id: '11111111-1111-1111-1111-111111111111',
  email: 'guest@arch3dar.local',
};

export function useCurrentUser(): { user: CurrentUser | null; refresh: () => Promise<void> } {
  return { user: FIXED_USER, refresh: async () => {} };
}
