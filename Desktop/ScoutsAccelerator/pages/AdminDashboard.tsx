





import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Rank, Requirement, User, Troop } from '../types';
import { SqlInstructions } from '../components/SqlInstructions';

type Tab = 'ranks' | 'troops' | 'users' | 'db_setup';

const EditIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.5L15.232 5.232z" /></svg>;
const DeleteIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>;
const PlusIcon = () => <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" /></svg>;

const ADMIN_SQL = `-- This script sets up the recommended Row Level Security (RLS) policies.
-- Run this in your Supabase SQL Editor to fix permission issues.
-- It's safe to run this multiple times.

-- Note: Ensure RLS is enabled on ALL of these tables in your Supabase dashboard:
-- profiles, ranks, requirements, troops, sign_off_requests, completed_requirements

-- ========= PROFILES TABLE POLICIES =========
DROP POLICY IF EXISTS "Allow individual user read access to own profile" ON public.profiles;
CREATE POLICY "Allow individual user read access to own profile"
ON public.profiles FOR SELECT
USING ( auth.uid() = id );

DROP POLICY IF EXISTS "Allow individual user to update own profile" ON public.profiles;
CREATE POLICY "Allow individual user to update own profile"
ON public.profiles FOR UPDATE
USING ( auth.uid() = id )
WITH CHECK ( auth.uid() = id );

-- Allow users to see other members of their own troop.
-- THIS IS CRUCIAL for Scoutmasters to see their scouts.
DROP POLICY IF EXISTS "Allow troop members to view each other" ON public.profiles;
CREATE POLICY "Allow troop members to view each other"
ON public.profiles FOR SELECT
USING (
  troop_id IS NOT NULL AND
  troop_id IN (
    SELECT troop_id FROM public.profiles WHERE id = auth.uid()
  )
);

-- Admins need to read all profiles for user management.
DROP POLICY IF EXISTS "Allow admin to read all profiles" ON public.profiles;
CREATE POLICY "Allow admin to read all profiles"
ON public.profiles FOR SELECT
USING ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' );


-- ========= RANKS TABLE POLICIES =========
DROP POLICY IF EXISTS "Allow authenticated read access to ranks" ON public.ranks;
CREATE POLICY "Allow authenticated read access to ranks"
ON public.ranks FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "Allow admin full access to ranks" ON public.ranks;
CREATE POLICY "Allow admin full access to ranks"
ON public.ranks FOR ALL
USING ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' )
WITH CHECK ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' );


-- ========= REQUIREMENTS TABLE POLICIES =========
DROP POLICY IF EXISTS "Allow authenticated users to read requirements" ON public.requirements;
CREATE POLICY "Allow authenticated users to read requirements"
ON public.requirements FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "Allow admins full access to requirements" ON public.requirements;
CREATE POLICY "Allow admins full access to requirements"
ON public.requirements FOR ALL
USING ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' )
WITH CHECK ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' );


-- ========= TROOPS TABLE POLICIES =========
DROP POLICY IF EXISTS "Allow authenticated read access to troops" ON public.troops;
CREATE POLICY "Allow authenticated read access to troops"
ON public.troops FOR SELECT
TO authenticated
USING (true);

DROP POLICY IF EXISTS "Allow scoutmasters to create troops" ON public.troops;
CREATE POLICY "Allow scoutmasters to create troops"
ON public.troops FOR INSERT
WITH CHECK ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'scoutmaster' AND scoutmaster_id = auth.uid() );

DROP POLICY IF EXISTS "Allow scoutmaster to update their own troop" ON public.troops;
CREATE POLICY "Allow scoutmaster to update their own troop"
ON public.troops FOR UPDATE
USING ( scoutmaster_id = auth.uid() );

DROP POLICY IF EXISTS "Allow admin full access to troops" ON public.troops;
CREATE POLICY "Allow admin full access to troops"
ON public.troops FOR ALL
USING ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' );


-- ========= SIGN_OFF_REQUESTS TABLE POLICIES =========
DROP POLICY IF EXISTS "Allow scouts to create sign-off requests" ON public.sign_off_requests;
CREATE POLICY "Allow scouts to create sign-off requests"
ON public.sign_off_requests FOR INSERT
WITH CHECK ( scout_id = auth.uid() );

DROP POLICY IF EXISTS "Allow troop members to see sign-off requests" ON public.sign_off_requests;
CREATE POLICY "Allow troop members to see sign-off requests"
ON public.sign_off_requests FOR SELECT
USING ( troop_id IN (SELECT troop_id FROM public.profiles WHERE id = auth.uid()) );

DROP POLICY IF EXISTS "Allow leaders to update sign-off requests" ON public.sign_off_requests;
CREATE POLICY "Allow leaders to update sign-off requests"
ON public.sign_off_requests FOR UPDATE
USING ( troop_id IN (SELECT troop_id FROM public.profiles WHERE id = auth.uid()) );

DROP POLICY IF EXISTS "Allow admin to manage sign-off requests" ON public.sign_off_requests;
CREATE POLICY "Allow admin to manage sign-off requests"
ON public.sign_off_requests FOR ALL
USING ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' );


-- ========= COMPLETED_REQUIREMENTS TABLE POLICIES =========
DROP POLICY IF EXISTS "Allow user to see own completed requirements" ON public.completed_requirements;
CREATE POLICY "Allow user to see own completed requirements"
ON public.completed_requirements FOR SELECT
USING ( user_id = auth.uid() );

DROP POLICY IF EXISTS "Allow leaders to insert completed requirements" ON public.completed_requirements;
CREATE POLICY "Allow leaders to insert completed requirements"
ON public.completed_requirements FOR INSERT
WITH CHECK (
  signed_off_by = auth.uid() AND
  EXISTS (
    SELECT 1 FROM public.profiles scout_profile
    WHERE
      scout_profile.id = user_id AND
      scout_profile.troop_id = (SELECT troop_id FROM public.profiles WHERE id = auth.uid())
  )
);

DROP POLICY IF EXISTS "Allow admin to manage completed requirements" ON public.completed_requirements;
CREATE POLICY "Allow admin to manage completed requirements"
ON public.completed_requirements FOR ALL
USING ( (SELECT role FROM public.profiles WHERE id = auth.uid()) = 'admin' );
`;

const DatabaseSetup: React.FC = () => {
    return (
        <SqlInstructions
            title="Database Security Setup"
            description="The following SQL script contains the recommended set of Row Level Security (RLS) policies for the application to function correctly for all roles. If you are having issues with permissions (e.g., scoutmasters not seeing their troop, unable to add/edit content, or data not appearing), running this script in your Supabase project should resolve them."
            sql={ADMIN_SQL}
        />
    );
};

interface RequirementModalProps {
    rankId: string;
    requirement: Requirement | null; // null for new, Requirement object for edit
    onSave: (req: Requirement) => Promise<void>;
    onClose: () => void;
}

const RequirementModal: React.FC<RequirementModalProps> = ({ rankId, requirement, onSave, onClose }) => {
    const [description, setDescription] = useState(requirement?.description || '');
    const [lessonHtml, setLessonHtml] = useState((requirement?.lesson_content as any)?.html || '<h1>New Lesson</h1>\n<p>Add lesson content here using HTML.</p>');
    const [error, setError] = useState('');
    const [isSaving, setIsSaving] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        if (!description.trim()) {
            setError('Description cannot be empty.');
            return;
        }
        setIsSaving(true);
        try {
            const newRequirementData: Requirement = {
                id: requirement?.id || '', // id will be generated by addRequirement if new
                rank_id: rankId,
                description: description,
                lesson_content: { html: lessonHtml },
            };
            await onSave(newRequirementData);
            onClose();
        } catch (err: any) {
            setError(`Failed to save requirement: ${err.message}`);
        } finally {
            setIsSaving(false);
        }
    };

    return (
        <div className="fixed inset-0 bg-black/60 z-50 flex justify-center items-center p-4" aria-modal="true" role="dialog">
            <form onSubmit={handleSubmit} className="bg-secondary rounded-xl border border-border-color w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
                <div className="p-4 border-b border-border-color">
                    <h3 className="text-xl font-bold text-text-primary">{requirement ? 'Edit' : 'Add'} Requirement</h3>
                </div>
                <div className="p-4 space-y-4 overflow-y-auto">
                    {error && <div className="bg-red-900/50 border border-red-500/30 text-red-200 p-3 rounded-lg text-sm" role="alert">{error}</div>}
                    <div>
                        <label htmlFor="req-desc" className="text-sm font-medium text-text-secondary block mb-2">Description</label>
                        <textarea
                            id="req-desc"
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            className="w-full h-24 px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-2 focus:ring-accent focus:border-accent"
                            required
                        />
                    </div>
                    <div>
                        <label htmlFor="req-lesson" className="text-sm font-medium text-text-secondary block mb-2">Lesson Content (HTML)</label>
                        <textarea
                            id="req-lesson"
                            value={lessonHtml}
                            onChange={(e) => setLessonHtml(e.target.value)}
                            className="w-full h-48 px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-2 focus:ring-accent focus:border-accent font-mono text-sm"
                        />
                    </div>
                </div>
                 <div className="p-4 border-t border-border-color mt-auto flex justify-end gap-3 bg-secondary/50 rounded-b-xl">
                    <button onClick={onClose} type="button" className="px-4 py-2 rounded-md bg-border-color text-text-primary hover:bg-primary/50 transition-colors">Cancel</button>
                    <button type="submit" disabled={isSaving} className="px-4 py-2 rounded-md bg-accent text-white hover:bg-accent-hover disabled:opacity-50 disabled:cursor-wait transition-colors">
                        {isSaving ? 'Saving...' : 'Save Requirement'}
                    </button>
                </div>
            </form>
        </div>
    );
};

const RanksManager: React.FC = () => {
    const { ranks, addRank, updateRank, deleteRank, addRequirement, updateRequirement, deleteRequirement } = useAuth();
    const [openRankId, setOpenRankId] = useState<string | null>(null);
    const [editingRank, setEditingRank] = useState<Rank | null>(null);
    
    const [reqModalState, setReqModalState] = useState<{ isOpen: boolean; rankId: string | null; requirement: Requirement | null; }>({
        isOpen: false,
        rankId: null,
        requirement: null,
    });

    const handleEditRank = (rank: Rank) => {
        setEditingRank({ ...rank });
    };

    const handleSaveRank = async () => {
        if (editingRank) {
            await updateRank(editingRank.id, editingRank.name, editingRank.icon, editingRank.sort_order);
            setEditingRank(null);
        }
    };

    const handleDeleteRank = async (rankId: string) => {
        if (window.confirm("Are you sure you want to delete this rank and all its requirements?")) {
            await deleteRank(rankId);
        }
    };
    
    const handleOpenAddRequirement = (rankId: string) => {
        setReqModalState({ isOpen: true, rankId: rankId, requirement: null });
    };

    const handleOpenEditRequirement = (req: Requirement) => {
        setReqModalState({ isOpen: true, rankId: req.rank_id, requirement: req });
    };

    const handleCloseReqModal = () => {
        setReqModalState({ isOpen: false, rankId: null, requirement: null });
    };

    const handleSaveRequirement = async (reqData: Requirement) => {
        if (reqModalState.rankId) {
            if (reqModalState.requirement) { // It's an edit
                await updateRequirement(reqModalState.rankId, reqModalState.requirement.id, reqData.description, (reqData.lesson_content as any).html);
            } else { // It's a new requirement
                await addRequirement(reqModalState.rankId, reqData.description, (reqData.lesson_content as any).html);
            }
        }
    };

    const handleDeleteRequirement = async (rankId: string, reqId: string) => {
        if (window.confirm("Are you sure you want to delete this requirement?")) {
            await deleteRequirement(rankId, reqId);
        }
    };

    return (
        <div className="space-y-4">
             <button onClick={() => {
                 const newName = prompt("Enter new rank name:");
                 if(newName) addRank(newName, "<svg></svg>");
             }} className="flex items-center gap-2 rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover transition-colors">
                <PlusIcon/> Add New Rank
            </button>
            {ranks.map(rank => (
                <div key={rank.id} className="bg-secondary rounded-xl border border-border-color overflow-hidden">
                    {editingRank?.id === rank.id ? (
                        <div className="p-4 space-y-3">
                            <input value={editingRank.name} onChange={(e) => setEditingRank({...editingRank, name: e.target.value})} className="w-full bg-primary p-2 rounded"/>
                            <textarea value={editingRank.icon} onChange={(e) => setEditingRank({...editingRank, icon: e.target.value})} className="w-full bg-primary p-2 rounded font-mono text-xs h-24"/>
                            <input type="number" value={editingRank.sort_order} onChange={(e) => setEditingRank({...editingRank, sort_order: parseInt(e.target.value)})} className="w-full bg-primary p-2 rounded"/>
                            <div className="flex gap-2">
                                <button onClick={handleSaveRank} className="bg-accent text-white px-4 py-1 rounded">Save</button>
                                <button onClick={() => setEditingRank(null)} className="bg-border-color px-4 py-1 rounded">Cancel</button>
                            </div>
                        </div>
                    ) : (
                        <div className="flex justify-between items-center p-4">
                            <div className="flex items-center gap-4 cursor-pointer" onClick={() => setOpenRankId(openRankId === rank.id ? null : rank.id)}>
                                <div dangerouslySetInnerHTML={{ __html: rank.icon }} />
                                <span className="font-bold text-lg text-text-primary">{rank.name}</span>
                                <span className="text-xs text-text-secondary">(Order: {rank.sort_order})</span>
                            </div>
                            <div className="flex gap-2">
                               <button onClick={() => handleEditRank(rank)} className="p-2 text-text-secondary hover:text-accent"><EditIcon /></button>
                               <button onClick={() => handleDeleteRank(rank.id)} className="p-2 text-text-secondary hover:text-red-500"><DeleteIcon/></button>
                            </div>
                        </div>
                    )}
                    {openRankId === rank.id && (
                         <div className="bg-primary/50 p-4 space-y-2">
                            <h4 className="font-semibold text-text-primary border-b border-border-color pb-2 mb-2">Requirements</h4>
                            {rank.requirements.map(req => (
                                <div key={req.id} className="flex justify-between items-center bg-primary p-2 rounded-md">
                                    <p className="text-sm text-text-secondary flex-1 pr-2">{req.description}</p>
                                    <div className="flex gap-2">
                                        <button onClick={() => handleOpenEditRequirement(req)} className="p-2 text-text-secondary hover:text-accent"><EditIcon /></button>
                                        <button onClick={() => handleDeleteRequirement(rank.id, req.id)} className="p-2 text-text-secondary hover:text-red-500"><DeleteIcon/></button>
                                    </div>
                                </div>
                            ))}
                            {rank.requirements.length === 0 && <p className="text-sm text-text-secondary italic">No requirements yet.</p>}
                            <button onClick={() => handleOpenAddRequirement(rank.id)} className="mt-2 flex items-center gap-2 text-accent text-sm font-semibold hover:underline">
                                <PlusIcon /> Add Requirement
                            </button>
                         </div>
                    )}
                </div>
            ))}
            {reqModalState.isOpen && reqModalState.rankId && (
                <RequirementModal
                    rankId={reqModalState.rankId}
                    requirement={reqModalState.requirement}
                    onSave={handleSaveRequirement}
                    onClose={handleCloseReqModal}
                />
            )}
        </div>
    );
};

const TroopsManager: React.FC = () => {
    const { getAllTroops, deleteTroop, allProfiles, getUserById } = useAuth();
    const [searchTerm, setSearchTerm] = useState('');
    const [expandedTroopId, setExpandedTroopId] = useState<string | null>(null);

    const troops = getAllTroops();
    
    const getScoutmaster = (id: string) => getUserById(id);

    const handleDeleteTroop = async (e: React.MouseEvent, troopId: string) => {
        e.stopPropagation(); 
        if (window.confirm("Are you sure you want to delete this troop? This will un-assign all its members.")) {
            await deleteTroop(troopId);
        }
    };

    const toggleExpand = (troopId: string) => {
        setExpandedTroopId(expandedTroopId === troopId ? null : troopId);
    };

    const filteredTroops = troops.filter(troop => {
        const scoutmaster = getScoutmaster(troop.scoutmasterId);
        const members = troop.members;
        const searchLower = searchTerm.toLowerCase();

        if (!searchTerm) return true;
        if (troop.name.toLowerCase().includes(searchLower)) return true;
        if (scoutmaster?.name?.toLowerCase().includes(searchLower)) return true;
        if (scoutmaster?.email?.toLowerCase().includes(searchLower)) return true;
        if (members.some(m => m.name?.toLowerCase().includes(searchLower))) return true;
        if (members.some(m => m.email?.toLowerCase().includes(searchLower))) return true;
        return false;
    });

    return (
        <div>
            <div className="mb-4">
                <input
                    type="text"
                    placeholder="Search by troop name, member name, or email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-accent focus:border-accent"
                />
            </div>
            <div className="space-y-3">
                {filteredTroops.map(troop => {
                    const scoutmaster = getScoutmaster(troop.scoutmasterId);
                    const troopMembers = troop.members;

                    return (
                        <div key={troop.id} className="bg-secondary rounded-lg border border-border-color transition-all duration-300">
                            <div className="flex justify-between items-center p-4 cursor-pointer hover:bg-primary/50" onClick={() => toggleExpand(troop.id)}>
                                <div>
                                    <p className="font-bold text-text-primary">{troop.name}</p>
                                    <p className="text-sm text-text-secondary">Scoutmaster: {scoutmaster?.name || troop.scoutmasterId}</p>
                                </div>
                                <div className="flex items-center gap-4">
                                     <span className="text-sm text-text-secondary">{troop.members.length} Scout{troop.members.length !== 1 ? 's' : ''}</span>
                                     <span className="text-sm font-mono bg-primary px-2 py-1 rounded">Code: {troop.joinCode}</span>
                                     <button onClick={(e) => handleDeleteTroop(e, troop.id)} className="p-2 text-text-secondary hover:text-red-500 z-10"><DeleteIcon/></button>
                                     <svg className={`w-5 h-5 text-text-secondary transform transition-transform ${expandedTroopId === troop.id ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </div>
                            {expandedTroopId === troop.id && (
                                <div className="p-4 border-t border-border-color space-y-2 bg-primary/30">
                                    <h5 className="font-semibold text-text-primary">Members</h5>
                                    {troopMembers.length > 0 ? (
                                        troopMembers.map(member => (
                                            <div key={member.id} className="bg-primary p-2 rounded-md">
                                                <p className="font-medium text-text-secondary">{member.name || 'N/A'} ({member.role})</p>
                                                <p className="text-xs text-text-secondary font-mono">{member.email}</p>
                                            </div>
                                        ))
                                    ) : (
                                        <p className="text-sm italic text-text-secondary">No members in this troop.</p>
                                    )}
                                </div>
                            )}
                        </div>
                    );
                })}
                 {filteredTroops.length === 0 && (
                    <div className="text-center p-8 bg-secondary rounded-lg border border-border-color">
                        <p className="text-text-secondary">No troops found matching your search.</p>
                    </div>
                 )}
            </div>
        </div>
    );
};

const UsersManager: React.FC = () => {
    const { allProfiles, deleteUser, getAllTroops } = useAuth();
    const troops = getAllTroops();

    const handleDeleteUser = async (userId: string) => {
        if (window.confirm(`Are you sure you want to delete this user's profile? This action is irreversible and will un-assign them from any troop, but will not delete their login credentials.`)) {
            await deleteUser(userId);
        }
    };
    
    return (
        <div className="space-y-3">
             {allProfiles.map(user => {
                const userTroop = user.troopId ? troops.find(t => t.id === user.troopId) : null;
                return (
                    <div key={user.id} className="bg-secondary p-4 rounded-lg border border-border-color flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                        <div className="flex-1">
                            <p className="font-bold text-text-primary">{user.name || 'N/A'}</p>
                            <p className="text-sm text-text-secondary">{user.email}</p>
                        </div>
                        <div className="flex items-center gap-4 flex-wrap">
                            <span className="text-sm font-medium bg-primary px-3 py-1 rounded-full">{user.role || 'Onboarding'}</span>
                            <span className="text-sm text-text-secondary">
                                Troop: {userTroop ? <span className="font-semibold text-text-primary">{userTroop.name}</span> : 'Unassigned'}
                            </span>
                            <button onClick={() => handleDeleteUser(user.id)} className="p-2 text-text-secondary hover:text-red-500 disabled:opacity-30 disabled:cursor-not-allowed" disabled={user.role === 'admin'}>
                                <DeleteIcon/>
                            </button>
                        </div>
                    </div>
                )
             })}
        </div>
    );
};


export const AdminDashboard: React.FC = () => {
    const [activeTab, setActiveTab] = useState<Tab>('ranks');

    const getTabClass = (tabName: Tab) => {
        return activeTab === tabName 
            ? 'bg-accent text-white' 
            : 'bg-secondary text-text-secondary hover:bg-primary';
    };

    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-text-primary mb-2">Admin Dashboard</h1>
            <p className="text-lg text-text-secondary mb-6">Global application management.</p>
            
            <div className="flex space-x-2 border-b border-border-color mb-6 overflow-x-auto pb-1">
                <button onClick={() => setActiveTab('ranks')} className={`px-4 py-2 rounded-t-lg font-semibold transition-colors flex-shrink-0 ${getTabClass('ranks')}`}>Manage Ranks</button>
                <button onClick={() => setActiveTab('troops')} className={`px-4 py-2 rounded-t-lg font-semibold transition-colors flex-shrink-0 ${getTabClass('troops')}`}>Manage Troops</button>
                <button onClick={() => setActiveTab('users')} className={`px-4 py-2 rounded-t-lg font-semibold transition-colors flex-shrink-0 ${getTabClass('users')}`}>Manage Users</button>
                <button onClick={() => setActiveTab('db_setup')} className={`px-4 py-2 rounded-t-lg font-semibold transition-colors flex-shrink-0 ${getTabClass('db_setup')}`}>DB Setup</button>
            </div>
            
            <div>
                {activeTab === 'ranks' && <RanksManager />}
                {activeTab === 'troops' && <TroopsManager />}
                {activeTab === 'users' && <UsersManager />}
                {activeTab === 'db_setup' && <DatabaseSetup />}
            </div>
        </div>
    );
};