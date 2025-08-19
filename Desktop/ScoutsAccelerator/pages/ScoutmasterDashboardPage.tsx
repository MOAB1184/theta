

import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useData } from '../hooks/useData';
import { User, Rank, Troop } from '../types';


const TroopRoster: React.FC<{ members: User[]; ranks: Rank[] }> = ({ members, ranks }) => {
    const getRankName = (rankId?: string | null) => {
        return ranks.find(r => r.id === rankId)?.name || 'N/A';
    };

    return (
        <div className="mt-4 max-h-60 overflow-y-auto pr-2">
            {members.length === 0 ? (
                <p className="text-text-secondary italic">No scouts have joined your troop yet.</p>
            ) : (
                <div className="space-y-2">
                    {members.map(member => (
                        <div key={member.id} className="flex justify-between items-center bg-primary p-2 rounded-md">
                            <div>
                                <p className="font-semibold text-text-primary">{member.name || member.email}</p>
                                <p className="text-sm text-text-secondary">{member.email}</p>
                            </div>
                            <span className="text-sm font-medium bg-accent/20 text-accent px-2 py-1 rounded-full">
                                {getRankName(member.currentRankId)}
                            </span>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

const TroopSettings: React.FC<{ troop: Troop; ranks: Rank[]; onSettingsChange: (newMinRankId: string) => Promise<void> }> = ({ troop, ranks, onSettingsChange }) => {
    const [minRankId, setMinRankId] = useState(troop.minRankForSignOffId || '');
    const [isEditing, setIsEditing] = useState(false);
    const [isSaving, setIsSaving] = useState(false);

    const handleSave = async () => {
        setIsSaving(true);
        await onSettingsChange(minRankId);
        setIsEditing(false);
        setIsSaving(false);
    };
    
    const currentRankName = ranks.find(r => r.id === troop.minRankForSignOffId)?.name || 'Not Set';
    
    return (
        <div className="mt-4">
            {isEditing ? (
                <div className="space-y-3">
                     <select
                        value={minRankId}
                        onChange={(e) => setMinRankId(e.target.value)}
                        className="w-full px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-accent focus:border-accent"
                    >
                        {ranks.map(rank => (
                            <option key={rank.id} value={rank.id}>{rank.name}</option>
                        ))}
                    </select>
                    <div className="flex gap-2">
                        <button onClick={handleSave} disabled={isSaving} className="flex-1 rounded-md bg-accent px-3 py-1.5 text-sm font-semibold text-white disabled:opacity-50">{isSaving ? 'Saving...' : 'Save'}</button>
                        <button onClick={() => setIsEditing(false)} className="flex-1 rounded-md bg-border-color px-3 py-1.5 text-sm font-semibold text-text-secondary">Cancel</button>
                    </div>
                </div>
            ) : (
                <div className="flex justify-between items-center bg-primary p-3 rounded-md">
                    <div>
                        <p className="text-sm text-text-secondary">Minimum Rank for Sign-off</p>
                        <p className="font-semibold text-text-primary">{currentRankName}</p>
                    </div>
                    <button onClick={() => setIsEditing(true)} className="text-accent text-sm font-semibold">Edit</button>
                </div>
            )}
        </div>
    );
};


export const ScoutmasterDashboardPage: React.FC = () => {
    const { user, getTroop, getTroopMembers, updateTroopSettings } = useAuth();
    const { ranks } = useData();
    const [troop, setTroop] = useState<Troop | null>(null);
    const [troopMembers, setTroopMembers] = useState<User[]>([]);

    useEffect(() => {
        if (user && user.troopId) {
            setTroop(getTroop(user.troopId) || null);
            setTroopMembers(getTroopMembers(user.troopId));
        }
    }, [user, getTroop, getTroopMembers]);

    const handleSettingsChange = async (newMinRankId: string) => {
        if (troop) {
            await updateTroopSettings(troop.id, newMinRankId);
        }
    };
    
    const copyToClipboard = () => {
        if (troop?.joinCode) {
            navigator.clipboard.writeText(troop.joinCode).then(() => {
                alert('Join code copied to clipboard!');
            });
        }
    };
    
    return (
        <div className="max-w-7xl mx-auto">
            <h1 className="text-3xl font-bold text-text-primary mb-2">Scoutmaster Dashboard</h1>
            <p className="text-lg text-text-secondary mb-6">Manage your troop and view your scouts' progress.</p>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left Column */}
                <div className="space-y-6">
                    <div className="bg-secondary p-6 rounded-xl border border-border-color">
                        <h2 className="text-xl font-bold text-text-primary">Troop Roster</h2>
                        <p className="text-text-secondary mt-2">See all members of your troop and their current ranks.</p>
                        <TroopRoster members={troopMembers} ranks={ranks} />
                    </div>
                </div>
                
                {/* Right Column */}
                <div className="space-y-6">
                    <div className="bg-secondary p-6 rounded-xl border border-border-color">
                        <h2 className="text-xl font-bold text-text-primary">Troop Settings</h2>
                        <p className="text-text-secondary mt-2">Manage settings for your entire troop.</p>
                        {troop && <TroopSettings troop={troop} ranks={ranks} onSettingsChange={handleSettingsChange} />}
                    </div>

                    <div className="bg-secondary p-6 rounded-xl border border-border-color">
                        <h2 className="text-xl font-bold text-text-primary">Troop Join Code</h2>
                        <p className="text-text-secondary mt-2">Share this code with new scouts.</p>
                        <div 
                            className="mt-4 bg-primary p-3 rounded-lg border border-border-color text-center group relative cursor-pointer"
                             onClick={copyToClipboard}
                        >
                            <p className="text-xl font-mono text-accent tracking-widest">{troop?.joinCode}</p>
                            <span className="absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity">
                                Copy Code
                            </span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
