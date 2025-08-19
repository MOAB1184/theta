

import React, { createContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { supabase } from '../services/supabase';
import { Session } from '@supabase/supabase-js';
import { User, Troop, UserRole, SignOffRequest, CompletedRequirement, Rank, Requirement } from '../types';
import { Database } from '../services/database.types';

type Profile = Database['public']['Tables']['profiles']['Row'];
type DbRank = Database['public']['Tables']['ranks']['Row'];
type DbRequirement = Database['public']['Tables']['requirements']['Row'];
type DbTroop = Database['public']['Tables']['troops']['Row'];
type DbSignOffRequest = Database['public']['Tables']['sign_off_requests']['Row'];
type DbCompletedRequirement = Database['public']['Tables']['completed_requirements']['Row'];

// Default ranks to seed the database if it's empty
const defaultRankIcon = `<svg xmlns="http://www.w3.org/2000/svg" class="h-8 w-8 text-accent" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.286zm0 13.036h.008v.008h-.008v-.008z" /></svg>`;

const DEFAULT_RANKS: Database['public']['Tables']['ranks']['Insert'][] = [
  { id: 'scout', name: 'Scout', icon: defaultRankIcon, sort_order: 1 },
  { id: 'tenderfoot', name: 'Tenderfoot', icon: defaultRankIcon, sort_order: 2 },
  { id: 'second-class', name: 'Second Class', icon: defaultRankIcon, sort_order: 3 },
  { id: 'first-class', name: 'First Class', icon: defaultRankIcon, sort_order: 4 },
  { id: 'star', name: 'Star', icon: defaultRankIcon, sort_order: 5 },
  { id: 'life', name: 'Life', icon: defaultRankIcon, sort_order: 6 },
  { id: 'eagle', name: 'Eagle', icon: defaultRankIcon, sort_order: 7 },
];


export type AuthResponse = {
  error: { message: string } | null;
};

interface AuthContextType {
  user: User | null;
  loading: boolean;
  error: string | null;
  // Auth
  login: (email: string, pass: string) => Promise<AuthResponse>;
  signup: (email: string, pass: string, name: string) => Promise<AuthResponse>;
  logout: () => Promise<{ error: null }>;
  updateUserOnboarding: (userId: string, role: UserRole, details: { troopId: string; currentRankId?: string }) => Promise<void>;
  // Data: Ranks & Requirements
  ranks: Rank[];
  addRank: (name: string, icon: string) => Promise<void>;
  updateRank: (rankId: string, newName: string, newIcon: string, newSortOrder: number) => Promise<void>;
  deleteRank: (rankId: string) => Promise<void>;
  addRequirement: (rankId: string, description: string, lessonHtml: string) => Promise<void>;
  updateRequirement: (rankId: string, reqId: string, newDescription: string, newLessonHtml: string) => Promise<void>;
  deleteRequirement: (rankId: string, reqId: string) => Promise<void>;
  // Data: Troops
  getTroop: (troopId: string) => Troop | undefined;
  getAllTroops: () => Troop[];
  createTroop: (troopName: string, scoutmasterId: string, minRankId: string) => Promise<Troop>;
  joinTroop: (joinCode: string, userId: string, currentRankId: string) => Promise<{ success: boolean; message: string }>;
  deleteTroop: (troopId: string) => Promise<void>;
  updateTroopSettings: (troopId: string, newMinRankId: string) => Promise<void>;
  // Data: Users & SignOffs
  allProfiles: User[];
  deleteUser: (userId: string) => Promise<void>;
  getUserById: (id: string) => User | undefined;
  getTroopMembers: (troopId: string) => User[];
  isUserEligibleForSignOff: (user: User) => boolean;
  createSignOffRequest: (rankId: string, reqId: string) => Promise<{success: boolean, message: string}>;
  getSignOffRequests: (troopId: string) => SignOffRequest[];
  acceptSignOffRequest: (requestId: string) => Promise<void>;
  updateSignOffStatus: (requestId: string, newStatus: 'approved' | 'rejected') => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [session, setSession] = useState<Session | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // In-memory state for all app data, sourced from Supabase
  const [allProfiles, setAllProfiles] = useState<User[]>([]);
  const [allTroops, setAllTroops] = useState<Troop[]>([]);
  const [allSignOffRequests, setAllSignOffRequests] = useState<SignOffRequest[]>([]);
  const [ranks, setRanks] = useState<Rank[]>([]);

  // Fetch all data from Supabase and transform it for the application
  const fetchCoreData = async (session: Session | null) => {
    setLoading(true);
    setError(null);
    if (!session) {
      // Clear all data on logout
      setRanks([]);
      setAllProfiles([]);
      setAllTroops([]);
      setAllSignOffRequests([]);
      setUser(null);
      setLoading(false);
      return;
    }

    // Attempt to fetch ranks
    let { data: ranksData, error: ranksError } = await (supabase as any).from('ranks').select('*').order('sort_order');

    // If ranks table is empty and we're logged in, seed it with defaults
    if (!ranksError && (!ranksData || ranksData.length === 0)) {
        console.log("No ranks found in database. Seeding with default ranks...");
        const { error: seedError } = await (supabase as any).from('ranks').insert(DEFAULT_RANKS);
        if (seedError) {
            console.error("Error seeding default ranks:", seedError);
            setError(`Database setup error: Could not create default ranks. This is likely due to your database's Row Level Security (RLS) policies. Please ensure the "ranks" table has an INSERT policy for authenticated users. Full error: ${seedError.message}`);
        } else {
            // Re-fetch ranks after seeding to ensure UI consistency
            const { data: newRanksData, error: newRanksError } = await (supabase as any).from('ranks').select('*').order('sort_order');
            if (newRanksError) {
              console.error("Error re-fetching ranks after seeding:", newRanksError);
            } else {
              ranksData = newRanksData;
            }
        }
    }

    // Explicitly select columns to avoid TS errors from circular dependencies in generated types.
    const { data: requirementsData, error: requirementsError } = await (supabase as any).from('requirements').select('*');
    const { data: profilesData, error: profilesError } = await (supabase as any).from('profiles').select('*');
    const { data: troopsData, error: troopsError } = await (supabase as any).from('troops').select('*');
    const { data: requestsData, error: requestsError } = await (supabase as any).from('sign_off_requests').select('*');
    
    const allErrors = [ranksError, requirementsError, profilesError, troopsError, requestsError].filter(Boolean);
    if (allErrors.length > 0) {
      const errorMsg = allErrors.map(e => e!.message).join('; ');
      console.error('Error fetching data:', errorMsg);
      setError(prev => prev ? `${prev}\nAdditionally: ${errorMsg}` : `Error fetching application data: ${errorMsg}`);
    }
    
    // --- Data Transformation (Adapter Layer) ---
    const appRanks: Rank[] = (ranksData || []).map((rank: DbRank) => ({
      id: rank.id,
      name: rank.name,
      icon: rank.icon,
      sort_order: rank.sort_order,
      requirements: (requirementsData || []).filter((req: DbRequirement) => req.rank_id === rank.id).map((req: DbRequirement) => ({
        id: req.id,
        description: req.description,
        lesson_content: req.lesson_content as { html: string },
        rank_id: req.rank_id
      }))
    }));
    
    const appProfiles: User[] = (profilesData || []).map((p: Profile) => ({
      id: p.id,
      email: session.user.id === p.id ? session.user.email! : `user-${p.id}`, // Only current user's email is certain
      role: p.role,
      troopId: p.troop_id,
      name: p.name,
      currentRankId: p.current_rank_id,
      completedRequirements: [], // Fetched separately below
    }));

    const appTroops: Troop[] = (troopsData || []).map((t: DbTroop) => ({
      id: t.id,
      name: t.name,
      scoutmasterId: t.scoutmaster_id,
      joinCode: t.join_code,
      members: appProfiles.filter(p => p.troopId === t.id),
      minRankForSignOffId: t.min_rank_for_sign_off_id,
    }));
    
    const allRequirements = appRanks.flatMap(r => r.requirements);
    const appRequests: SignOffRequest[] = (requestsData || []).map((r: DbSignOffRequest) => {
        const scout = appProfiles.find(p => p.id === r.scout_id);
        const acceptedBy = appProfiles.find(p => p.id === r.accepted_by);
        const finalizedBy = appProfiles.find(p => p.id === r.finalized_by);
        const requirement = allRequirements.find(req => req.id === r.requirement_id);
        return {
            id: r.id,
            scoutId: r.scout_id,
            scoutName: scout?.name || 'Unknown Scout',
            rankId: r.rank_id,
            requirementId: r.requirement_id,
            requirementDescription: requirement?.description || 'Unknown Requirement',
            status: r.status,
            troopId: r.troop_id,
            acceptedById: acceptedBy?.id,
            acceptedByName: acceptedBy?.name,
            finalizedById: finalizedBy?.id,
            finalizedByName: finalizedBy?.name,
        };
    });


    // Fetch completed requirements for the logged-in user
    const { data: completedData } = await (supabase as any).from('completed_requirements').select('*').eq('user_id', session.user.id);
    const appCompletedReqs: CompletedRequirement[] = (completedData || []).map((cr: DbCompletedRequirement) => ({
        requirement_id: cr.requirement_id,
        rank_id: cr.rank_id,
        completed_at: cr.completed_at,
        signed_off_by: cr.signed_off_by,
    }));

    const currentUserProfile = appProfiles.find(p => p.id === session.user.id);
    if (currentUserProfile) {
        currentUserProfile.email = session.user.email!; // ensure correct email
        currentUserProfile.completedRequirements = appCompletedReqs;
        setUser(currentUserProfile);
    } else {
        setUser(null)
    }

    setAllProfiles(appProfiles);
    setAllTroops(appTroops);
    setAllSignOffRequests(appRequests);
    setRanks(appRanks);
    setLoading(false);
  };
  
  // Listen to auth state changes
  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange(async (_event, session) => {
      setSession(session);
      await fetchCoreData(session);
    });

    // Initial check
    const checkInitialSession = async () => {
        // This is a safer way to get the session, avoiding a potential TypeError
        // if the API returns an error and a null data object. Such an unhandled
        // error would halt execution and cause the loading spinner to hang indefinitely.
        const { data, error } = await supabase.auth.getSession();
        
        if (error) {
            console.error("Error getting session:", error.message);
            setError(`Failed to initialize session: ${error.message}`);
            setLoading(false); // Ensure loading stops on a session error.
            return;
        }
        
        const session = data.session;
        setSession(session);
        await fetchCoreData(session);
    };
    checkInitialSession();

    return () => subscription.unsubscribe();
  }, []);

  const login = async (email: string, pass: string): Promise<AuthResponse> => {
    const { error } = await supabase.auth.signInWithPassword({ email, password: pass });
    return { error: error ? { message: error.message } : null };
  };

  const signup = async (email: string, pass: string, name: string): Promise<AuthResponse> => {
    const { error } = await supabase.auth.signUp({
      email,
      password: pass,
      options: {
        data: { name }, // This is used by the handle_new_user trigger
      },
    });
    // The trigger now handles profile creation, so no manual insert is needed.
    return { error: error ? { message: error.message } : null };
  };

  const logout = async (): Promise<{ error: null }> => {
    await supabase.auth.signOut();
    return { error: null };
  };

  const updateUserOnboarding = async (userId: string, role: UserRole, details: { troopId: string; currentRankId?: string }) => {
    const updatePayload: Database['public']['Tables']['profiles']['Update'] = {
      role: role,
      troop_id: details.troopId,
      current_rank_id: details.currentRankId,
    };
    
    const { error } = await (supabase as any).from('profiles').update(updatePayload).eq('id', userId);
    if (error) console.error("Error updating user onboarding:", error);
    await fetchCoreData(session);
  };

  const createTroop = async (troopName: string, scoutmasterId: string, minRankId: string): Promise<Troop> => {
    const joinCode = Math.random().toString(36).substring(2, 8).toUpperCase();
    const { data, error } = await (supabase as any).from('troops').insert({
        name: troopName,
        scoutmaster_id: scoutmasterId,
        min_rank_for_sign_off_id: minRankId,
        join_code: joinCode,
    }).select('*').single();

    if (error) throw error;
    if (!data) throw new Error("Troop creation failed: no data returned.");
    
    const typedData = data as DbTroop;

    await fetchCoreData(session);
    
    // The data returned from the insert is sufficient now. We find it in state for consistency.
    const newTroopInState = allTroops.find(t => t.id === typedData.id);
    if (!newTroopInState) {
        // Fallback in case state update is slow.
        const newTroop: Troop = {
            id: typedData.id,
            name: typedData.name,
            scoutmasterId: typedData.scoutmaster_id,
            joinCode: typedData.join_code,
            members: [],
            minRankForSignOffId: typedData.min_rank_for_sign_off_id,
        }
        return newTroop;
    }
    return newTroopInState;
  };

  const joinTroop = async (joinCode: string, userId: string, currentRankId: string): Promise<{ success: boolean; message: string }> => {
    const { data: troop, error } = await (supabase as any).from('troops').select('*').eq('join_code', joinCode.toUpperCase()).single();
    if (error || !troop) {
        return { success: false, message: 'Invalid troop join code.' };
    }
    
    const typedTroop = troop as DbTroop;
    
    // Now we update the profile with troop and role in one go.
    await updateUserOnboarding(userId, 'scout', { troopId: typedTroop.id, currentRankId });

    // No need to call fetchCoreData again, as updateUserOnboarding already does.
    return { success: true, message: 'Successfully joined troop!' };
  };
  
  const getTroopMembers = useCallback((troopId: string): User[] => {
    const troop = allTroops.find(t => t.id === troopId);
    if (!troop) {
        return [];
    }
    // The troop.members array contains all users in the troop. We just need to filter for scouts.
    return troop.members.filter(member => member.role === 'scout');
  }, [allTroops]);

  const getUserById = useCallback((id: string) => allProfiles.find(u => u.id === id), [allProfiles]);

  const getTroop = useCallback((troopId: string): Troop | undefined => allTroops.find(t => t.id === troopId), [allTroops]);
  
  const getAllTroops = useCallback((): Troop[] => allTroops, [allTroops]);

  const getSignOffRequests = useCallback((troopId: string): SignOffRequest[] => {
    return allSignOffRequests.filter(r => r.troopId === troopId);
  }, [allSignOffRequests]);

  const isUserEligibleForSignOff = useCallback((checkUser: User): boolean => {
    if (!checkUser || !checkUser.troopId || !checkUser.currentRankId) return false;
    if (checkUser.role === 'scoutmaster' || checkUser.role === 'admin') return true;
    const troop = getTroop(checkUser.troopId);
    if (!troop || !troop.minRankForSignOffId) return false;
    const userRankOrder = ranks.find(r => r.id === checkUser.currentRankId)?.sort_order;
    const requiredRankOrder = ranks.find(r => r.id === troop.minRankForSignOffId)?.sort_order;
    if (userRankOrder === undefined || requiredRankOrder === undefined) return false;
    return userRankOrder >= requiredRankOrder;
  }, [ranks, getTroop]);

  const createSignOffRequest = async (rankId: string, reqId: string): Promise<{success: boolean, message: string}> => {
    if (!user || !user.troopId) return { success: false, message: 'You must be logged in and part of a troop.' };
    const existing = allSignOffRequests.find(r => r.scoutId === user.id && r.requirementId === reqId && (r.status === 'pending' || r.status === 'accepted'));
    if (existing) return { success: false, message: 'You already have an active request for this requirement.' };

    const { error } = await (supabase as any).from('sign_off_requests').insert({
        scout_id: user.id,
        rank_id: rankId,
        requirement_id: reqId,
        troop_id: user.troopId,
        status: 'pending'
    });
    if (error) return { success: false, message: `Failed to create request: ${error.message}` };
    await fetchCoreData(session);
    return { success: true, message: 'Sign-off request sent successfully!' };
  };

  const acceptSignOffRequest = async (requestId: string) => {
    if (!user) return;
    await (supabase as any).from('sign_off_requests').update({ status: 'accepted', accepted_by: user.id }).eq('id', requestId);
    await fetchCoreData(session);
  };
  
  const updateSignOffStatus = async (requestId: string, newStatus: 'approved' | 'rejected') => {
    if (!user) return;
    const request = allSignOffRequests.find(r => r.id === requestId);
    if (!request) return;

    await (supabase as any).from('sign_off_requests').update({ status: newStatus, finalized_by: user.id }).eq('id', requestId);

    if (newStatus === 'approved') {
        const scout = allProfiles.find(p => p.id === request.scoutId);
        if(scout) {
            await (supabase as any).from('completed_requirements').insert({
                user_id: scout.id,
                requirement_id: request.requirementId,
                rank_id: request.rankId,
                signed_off_by: user.id
            });
        }
    }
    await fetchCoreData(session);
  };

  const updateTroopSettings = async (troopId: string, newMinRankId: string) => {
    await (supabase as any).from('troops').update({ min_rank_for_sign_off_id: newMinRankId }).eq('id', troopId);
    await fetchCoreData(session);
  };

  const deleteUser = async (userId: string) => {
    const userToDelete = allProfiles.find(u => u.id === userId);
    if (!userToDelete) {
        alert("Cannot delete: User not found.");
        return;
    }
    if (userToDelete.role === 'admin') {
      alert("Admins cannot be deleted from the dashboard.");
      return;
    }
    
    // Prevent deleting a user if they are the scoutmaster of any troop
    const isScoutmaster = allTroops.some(troop => troop.scoutmasterId === userId);
    if (isScoutmaster) {
        alert("This user is a scoutmaster of a troop. Please reassign the scoutmaster role or delete the troop before deleting this user.");
        return;
    }
    
    // This part is a protected operation and typically done via a server-side function.
    // The current implementation only removes the profile, not the auth user.
    console.warn("User deletion from auth.users is a protected operation and is not performed on the client. Only the user's profile will be removed.");
    
    const { error } = await (supabase as any).from('profiles').delete().eq('id', userToDelete.id);
    
    if (error) {
        alert(`Failed to delete user profile: ${error.message}`);
        console.error("Error deleting user profile:", error);
    }
    
    await fetchCoreData(session);
  };

  const deleteTroop = async (troopId: string) => {
    // First, safely un-assign all members from the troop
    const { error: updateError } = await (supabase as any)
      .from('profiles')
      .update({ troop_id: null })
      .eq('troop_id', troopId);

    if (updateError) {
      const message = `Failed to un-assign members from the troop. Deletion aborted. Error: ${updateError.message}`;
      console.error(message);
      alert(message);
      return; // Stop the process
    }

    // Now, delete the troop itself
    const { error: deleteError } = await (supabase as any).from('troops').delete().eq('id', troopId);
    if (deleteError) {
        const message = `Members were unassigned, but failed to delete the troop itself. Error: ${deleteError.message}`;
        console.error(message);
        alert(message);
    }

    await fetchCoreData(session);
  };

  const addRank = async (name: string, icon: string) => {
    const maxOrder = ranks.reduce((max, r) => Math.max(max, r.sort_order || 0), 0);
    await (supabase as any).from('ranks').insert({ id: name.toLowerCase().replace(/\s+/g, '-'), name, icon, sort_order: maxOrder + 1 });
    await fetchCoreData(session);
  };

  const updateRank = async (rankId: string, newName: string, newIcon: string, newSortOrder: number) => {
    await (supabase as any).from('ranks').update({ name: newName, icon: newIcon, sort_order: newSortOrder }).eq('id', rankId);
    await fetchCoreData(session);
  };

  const deleteRank = async (rankId: string) => {
    await (supabase as any).from('ranks').delete().eq('id', rankId);
    await fetchCoreData(session);
  };

  const addRequirement = async (rankId: string, description: string, lessonHtml: string) => {
    const reqId = `${rankId}_${Date.now()}`;
    const { error } = await (supabase as any).from('requirements').insert({
      id: reqId,
      rank_id: rankId,
      description,
      lesson_content: { html: lessonHtml },
    });
    
    if (error) {
        console.error("Error adding requirement:", error.message);
        throw new Error(`Failed to add requirement: ${error.message}`);
    }
    await fetchCoreData(session);
  };

  const updateRequirement = async (rankId: string, reqId: string, newDescription: string, newLessonHtml: string) => {
    const { error } = await (supabase as any).from('requirements').update({
      description: newDescription,
      lesson_content: { html: newLessonHtml },
    }).eq('id', reqId);

    if (error) {
        console.error("Error updating requirement:", error.message);
        throw new Error(`Failed to update requirement: ${error.message}`);
    }
    await fetchCoreData(session);
  };

  const deleteRequirement = async (rankId: string, reqId: string) => {
    await (supabase as any).from('requirements').delete().eq('id', reqId);
    await fetchCoreData(session);
  };

  const value: AuthContextType = {
    user,
    loading,
    error,
    login,
    signup,
    logout,
    updateUserOnboarding,
    createTroop,
    joinTroop,
    getTroopMembers,
    isUserEligibleForSignOff,
    createSignOffRequest,
    getSignOffRequests,
    acceptSignOffRequest,
    updateSignOffStatus,
    getTroop,
    ranks,
    getAllTroops,
    updateTroopSettings,
    allProfiles,
    getUserById,
    deleteTroop,
    deleteUser,
    addRank,
    updateRank,
    deleteRank,
    addRequirement,
    updateRequirement,
    deleteRequirement,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
