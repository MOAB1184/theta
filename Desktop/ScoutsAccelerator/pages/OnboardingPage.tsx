

import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { useNavigate } from 'react-router-dom';
import { UserRole } from '../types';

// By defining these components outside of OnboardingPage, we ensure they are not
// re-created on every render. This prevents the input fields from losing focus
// when the parent component's state changes.

const RoleSelector: React.FC<{ setRole: (role: UserRole) => void }> = ({ setRole }) => (
    <div className="space-y-4">
        <button onClick={() => setRole('scoutmaster')} className="w-full p-6 text-left bg-secondary hover:bg-primary border border-border-color rounded-lg transition-colors">
            <h3 className="text-xl font-bold text-text-primary">I'm a Scoutmaster</h3>
            <p className="text-text-secondary">I want to set up and manage my troop.</p>
        </button>
        <button onClick={() => setRole('scout')} className="w-full p-6 text-left bg-secondary hover:bg-primary border border-border-color rounded-lg transition-colors">
            <h3 className="text-xl font-bold text-text-primary">I'm a Scout</h3>
            <p className="text-text-secondary">I want to join my troop and start advancing.</p>
        </button>
    </div>
);

const ScoutmasterForm: React.FC<{ 
    onSubmit: (e: React.FormEvent) => void;
    troopName: string;
    setTroopName: (name: string) => void;
    minRankId: string;
    setMinRankId: (id: string) => void;
    isLoading: boolean;
}> = ({ onSubmit, troopName, setTroopName, minRankId, setMinRankId, isLoading }) => {
    const { ranks } = useAuth();
    return (
        <form onSubmit={onSubmit} className="space-y-4">
            <div>
                <label htmlFor="troopName" className="text-sm font-medium text-text-secondary block mb-2">Troop Name</label>
                <input 
                    id="troopName" 
                    value={troopName} 
                    onChange={(e) => setTroopName(e.target.value)}
                    className="w-full px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-accent focus:border-accent"
                    placeholder="e.g., Troop 42" 
                    required 
                />
            </div>
             <div>
                <label htmlFor="minRank" className="text-sm font-medium text-text-secondary block mb-2">Minimum Rank for Sign-offs</label>
                <select
                    id="minRank"
                    value={minRankId}
                    onChange={(e) => setMinRankId(e.target.value)}
                    className="w-full px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-accent focus:border-accent"
                    required
                >
                    <option value="" disabled>Select a rank</option>
                    {ranks.map(rank => (
                        <option key={rank.id} value={rank.id}>{rank.name}</option>
                    ))}
                </select>
            </div>
            <button type="submit" disabled={isLoading} className="w-full py-3 px-4 rounded-md text-sm font-medium text-white bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-wait">
                {isLoading ? 'Creating Troop...' : 'Create Troop'}
            </button>
        </form>
    );
};

const ScoutForm: React.FC<{
    onSubmit: (e: React.FormEvent) => void;
    joinCode: string;
    setJoinCode: (id: string) => void;
    currentRankId: string;
    setCurrentRankId: (id: string) => void;
    isLoading: boolean;
}> = ({ onSubmit, joinCode, setJoinCode, currentRankId, setCurrentRankId, isLoading }) => {
    const { ranks } = useAuth();
    return (
        <form onSubmit={onSubmit} className="space-y-4">
            <div>
                <label htmlFor="joinCode" className="text-sm font-medium text-text-secondary block mb-2">Troop Join Code</label>
                <input 
                    id="joinCode" 
                    value={joinCode} 
                    onChange={(e) => setJoinCode(e.target.value)}
                    className="w-full px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-accent focus:border-accent"
                    placeholder="Ask your Scoutmaster for the code" 
                    required 
                />
            </div>
            <div>
                <label htmlFor="currentRank" className="text-sm font-medium text-text-secondary block mb-2">Your Current Rank</label>
                <select
                    id="currentRank"
                    value={currentRankId}
                    onChange={(e) => setCurrentRankId(e.target.value)}
                    className="w-full px-4 py-2 bg-primary border border-border-color rounded-md text-text-primary focus:ring-accent focus:border-accent"
                    required
                >
                    <option value="" disabled>Select your rank</option>
                    {ranks.map(rank => (
                        <option key={rank.id} value={rank.id}>{rank.name}</option>
                    ))}
                </select>
            </div>
            <button type="submit" disabled={isLoading} className="w-full py-3 px-4 rounded-md text-sm font-medium text-white bg-accent hover:bg-accent-hover disabled:opacity-50 disabled:cursor-wait">
                {isLoading ? 'Joining...' : 'Join Troop'}
            </button>
        </form>
    );
};


export const OnboardingPage: React.FC = () => {
  const [role, setRole] = useState<UserRole | null>(null);
  const [troopName, setTroopName] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [minRankId, setMinRankId] = useState(''); 
  const [currentRankId, setCurrentRankId] = useState('');
  const [error, setError] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const navigate = useNavigate();
  const { user, ranks, updateUserOnboarding, createTroop, joinTroop } = useAuth();

  // Set default ranks once data is loaded to avoid re-render loops and bugs.
  useEffect(() => {
    if (ranks.length > 0) {
      // Set a sensible default for the scoutmaster form
      if (!minRankId) {
          const tenderfoot = ranks.find(r => r.id === 'tenderfoot');
          setMinRankId(tenderfoot?.id || ranks[1]?.id || ranks[0]?.id || '');
      }
      // Set a sensible default for the scout form
      if (!currentRankId) {
          setCurrentRankId(ranks[0]?.id || '');
      }
    }
  }, [ranks]);

  if (!user) {
    navigate('/login');
    return null;
  }

  const handleScoutmasterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!troopName.trim() || !minRankId) {
        setError('Please complete all fields.');
        return;
    }
    setIsLoading(true);
    try {
        const newTroop = await createTroop(troopName, user.id, minRankId);
        await updateUserOnboarding(user.id, 'scoutmaster', { troopId: newTroop.id });
        setGeneratedCode(newTroop.joinCode);
    } catch (err: any) {
        setError(err.message);
    } finally {
        setIsLoading(false);
    }
  };

  const handleScoutSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!joinCode.trim() || !currentRankId) {
        setError('Please complete all fields.');
        return;
    }
    setIsLoading(true);
    const { success, message } = await joinTroop(joinCode, user.id, currentRankId);
    if (success) {
        navigate('/dashboard');
    } else {
        setError(message);
    }
    setIsLoading(false);
  };

  const copyToClipboard = () => {
      navigator.clipboard.writeText(generatedCode).then(() => {
          alert('Join code copied to clipboard!');
      });
  };
  
  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-150px)]">
      <div className="w-full max-w-md p-8 space-y-6 bg-secondary rounded-xl border border-border-color shadow-lg">
        {generatedCode ? (
            <div className="text-center space-y-4">
                <h1 className="text-3xl font-bold text-text-primary">Troop Created!</h1>
                <p className="text-text-secondary">Share this join code with your scouts:</p>
                <div 
                    className="bg-primary p-4 rounded-lg border border-border-color group relative cursor-pointer"
                    onClick={copyToClipboard}
                    title="Copy to clipboard"
                >
                    <p className="text-2xl font-mono text-accent tracking-widest">{generatedCode}</p>
                     <span className="absolute -bottom-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs px-2 py-1 rounded-md opacity-0 group-hover:opacity-100 transition-opacity">
                        Copy Code
                    </span>
                </div>
                <button onClick={() => navigate('/dashboard')} className="w-full py-3 px-4 rounded-md text-sm font-medium text-white bg-accent hover:bg-accent-hover">Go to Dashboard</button>
            </div>
        ) : (
            <>
                <h1 className="text-3xl font-bold text-center text-text-primary">One Last Step...</h1>
                <p className="text-center text-text-secondary">{!role ? "Tell us who you are to get started." : `Setting up your ${role} account.`}</p>
                {error && <div className="bg-red-900/50 text-red-200 p-3 rounded-lg text-sm">{error}</div>}
                
                {!role ? (
                    <RoleSelector setRole={setRole} />
                ) : role === 'scoutmaster' ? (
                    <ScoutmasterForm 
                        onSubmit={handleScoutmasterSubmit} 
                        troopName={troopName} 
                        setTroopName={setTroopName} 
                        minRankId={minRankId}
                        setMinRankId={setMinRankId}
                        isLoading={isLoading}
                    />
                ) : (
                    <ScoutForm 
                        onSubmit={handleScoutSubmit} 
                        joinCode={joinCode} 
                        setJoinCode={setJoinCode} 
                        currentRankId={currentRankId}
                        setCurrentRankId={setCurrentRankId}
                        isLoading={isLoading}
                    />
                )}

                {role && <button onClick={() => setRole(null)} className="text-sm text-center w-full mt-4 text-text-secondary hover:text-text-primary"> &larr; Back</button>}
            </>
        )}
      </div>
    </div>
  );
};
