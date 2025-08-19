
import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { Link } from 'react-router-dom';
import { Troop } from '../types';

export const DashboardPage: React.FC = () => {
    const { user, getTroop } = useAuth();
    const [troop, setTroop] = useState<Troop | null>(null);

    useEffect(() => {
        if (user?.troopId) {
            const currentTroop = getTroop(user.troopId);
            setTroop(currentTroop || null);
        } else {
            setTroop(null);
        }
    }, [user, getTroop]);

    const copyToClipboard = () => {
        if (troop?.joinCode) {
            navigator.clipboard.writeText(troop.joinCode).then(() => {
                alert('Join code copied to clipboard!');
            });
        }
    };

    // Scout and Admin View
    const ScoutView = () => (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-secondary p-6 rounded-xl border border-border-color flex flex-col justify-between hover:border-accent transition-colors">
                <div>
                    <h2 className="text-2xl font-bold text-text-primary">Advance Your Rank</h2>
                    <p className="text-text-secondary mt-2">
                        View requirements, learn new skills, and track your progress toward your next rank.
                    </p>
                </div>
                <Link 
                    to="/advancement" 
                    className="mt-6 inline-block w-full text-center bg-accent text-white font-semibold py-3 px-6 rounded-lg hover:bg-accent-hover transition duration-300 shadow-[0_0_15px_theme(colors.accent/0.4)]"
                >
                    Go to Advancement
                </Link>
            </div>

            <div className="bg-secondary p-6 rounded-xl border border-border-color flex flex-col justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-text-primary">Time to Eagle</h2>
                    <p className="text-text-secondary mt-2">
                        Your current rank is <span className="font-semibold text-scout-green">Scout</span>. Keep up the great work!
                    </p>
                    {/* Progress bar could go here in the future */}
                </div>
                    <p className="text-sm text-text-secondary mt-6 italic">Further progress tracking coming soon.</p>
            </div>
        </div>
    );

    // Scoutmaster View
    const ScoutmasterView = () => (
         <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-secondary p-6 rounded-xl border border-border-color flex flex-col justify-between hover:border-accent transition-colors">
                <div>
                    <h2 className="text-2xl font-bold text-text-primary">Manage Your Troop</h2>
                    <p className="text-text-secondary mt-2">
                        View your troop roster, manage sign-offs, and assign permissions.
                    </p>
                </div>
                <Link 
                    to="/scoutmaster" 
                    className="mt-6 inline-block w-full text-center bg-accent text-white font-semibold py-3 px-6 rounded-lg hover:bg-accent-hover transition duration-300 shadow-[0_0_15px_theme(colors.accent/0.4)]"
                >
                    Go to Scoutmaster Dashboard
                </Link>
            </div>
             <div className="bg-secondary p-6 rounded-xl border border-border-color flex flex-col justify-between">
                <div>
                    <h2 className="text-2xl font-bold text-text-primary">Troop Join Code</h2>
                    <p className="text-text-secondary mt-2">
                        Share this code with new scouts so they can join your troop.
                    </p>
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
    );

    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-4xl font-bold text-text-primary mb-2">
                {troop?.name 
                    ? <>Welcome to <span className="text-accent">{troop.name}</span>, {user?.name || user?.email}!</> 
                    : <>Welcome, {user?.name || user?.email}!</>
                }
            </h1>
            <p className="text-lg text-text-secondary mb-8">
                {user?.role === 'scoutmaster' 
                    ? "Here's an overview of your troop management tools."
                    : "Ready to continue your journey? Let's get started."
                }
            </p>

            {user?.role === 'scoutmaster' ? <ScoutmasterView /> : <ScoutView />}
        </div>
    );
};
