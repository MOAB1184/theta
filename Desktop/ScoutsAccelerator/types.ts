

export type UserRole = 'scout' | 'scoutmaster' | 'admin';

export type CompletedRequirement = {
  requirement_id: string;
  rank_id: string;
  signed_off_by: string; // User ID (UUID)
  completed_at: string;
};

export type User = {
  id: string; // User's UUID from auth.users, PK in profiles
  email: string;
  name?: string | null; 
  // Role is null until the user completes the onboarding process.
  role: UserRole | null;
  troopId?: string | null;
  currentRankId?: string | null;
  completedRequirements?: CompletedRequirement[];
};

export type SignOffStatus = 'pending' | 'accepted' | 'approved' | 'rejected';

export type SignOffRequest = {
    id: string;
    scoutId: string;
    scoutName: string;
    rankId: string;
    requirementId: string;
    requirementDescription: string; // This is now populated at runtime
    status: SignOffStatus;
    troopId: string;
    acceptedById?: string | null; // UUID of user who accepted
    acceptedByName?: string | null; // Display name, populated at runtime
    finalizedById?: string | null; // UUID of user who approved/rejected
    finalizedByName?: string | null; // Display name, populated at runtime
};


export type Troop = {
    id: string; // UUID
    name: string;
    scoutmasterId: string; // UUID of the scoutmaster's profile
    joinCode: string; // The user-friendly join code
    members: User[]; // array of full User objects
    minRankForSignOffId?: string | null; // The minimum rank required to sign off on reqs
};

export type Requirement = {
  id: string;
  description: string;
  // `lesson_content` can be a rich object, typically with an HTML string.
  lesson_content: { [key: string]: any };
  rank_id: string;
};

export type Rank = {
  id: string;
  name: string;
  icon: string;
  requirements: Requirement[];
  sort_order: number;
};
