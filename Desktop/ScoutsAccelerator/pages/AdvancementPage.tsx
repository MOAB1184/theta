

import React, { useState } from 'react';
import { useData } from '../hooks/useData';
import { Link } from 'react-router-dom';
import { Rank } from '../types';
import { useAuth } from '../hooks/useAuth';

const RequirementItem: React.FC<{ rankId: string, reqId: string, description: string }> = ({ rankId, reqId, description }) => {
    const { user, createSignOffRequest } = useAuth();
    const [requestStatus, setRequestStatus] = useState('');
    
    const isCompleted = user?.completedRequirements?.some(cr => cr.requirement_id === reqId);

    const handleRequestSignOff = async () => {
        if (isCompleted) return;
        setRequestStatus('Sending...');
        try {
            const { success, message } = await createSignOffRequest(rankId, reqId);
            alert(message);
        } catch (error: any) {
            alert(`An error occurred: ${error.message}`);
        } finally {
            setRequestStatus('');
        }
    };

    return (
        <div className={`flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 border-t border-border-color transition-colors duration-200 ${isCompleted ? 'bg-green-900/10' : 'hover:bg-primary'}`}>
            <p className={`flex-1 pr-4 ${isCompleted ? 'line-through text-text-secondary' : 'text-text-primary'}`}>{description}</p>
            <div className="flex items-center gap-2 mt-3 sm:mt-0 flex-shrink-0 flex-wrap justify-start">
                {isCompleted ? (
                     <div className="flex items-center gap-2 text-scout-green font-semibold text-sm">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <span>Completed</span>
                    </div>
                ) : (
                    <>
                        <Link to={`/lesson/${rankId}/${reqId}`} className="rounded-md bg-secondary px-3 py-2 text-sm font-semibold text-text-primary ring-1 ring-inset ring-border-color hover:bg-primary transition-all duration-200">
                            Learn
                        </Link>
                        <Link to={`/quiz/${rankId}/${reqId}`} className="rounded-md bg-scout-blue/20 px-3 py-2 text-sm font-semibold text-scout-blue ring-1 ring-inset ring-scout-blue/30 hover:bg-scout-blue/30 transition-all duration-200">
                            Review
                        </Link>
                        <button 
                          onClick={handleRequestSignOff} 
                          disabled={!!requestStatus}
                          className="rounded-md bg-scout-green/20 px-3 py-2 text-sm font-semibold text-scout-green ring-1 ring-inset ring-scout-green/30 hover:bg-scout-green/30 transition-all duration-200 disabled:opacity-50 disabled:cursor-wait"
                        >
                            {requestStatus || 'Request Sign-off'}
                        </button>
                    </>
                )}
            </div>
        </div>
    );
};


const RankCard: React.FC<{ rank: Rank; isCompleted: boolean }> = ({ rank, isCompleted }) => {
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className={`bg-secondary rounded-xl border border-border-color mb-4 overflow-hidden transition-all duration-300 ${isCompleted ? 'opacity-60' : ''}`}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex justify-between items-center p-5 text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-primary rounded-xl"
            >
                <div className="flex items-center gap-4">
                    <div className="flex-shrink-0 text-accent" dangerouslySetInnerHTML={{ __html: rank.icon }} />
                    <h3 className={`text-xl font-bold text-text-primary ${isCompleted ? 'line-through' : ''}`}>{rank.name}</h3>
                </div>
                <svg className={`w-6 h-6 transform transition-transform text-text-secondary ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
            </button>
            {isOpen && (
                <div className="bg-primary/50">
                    {rank.requirements.length > 0 ? rank.requirements.map(req => (
                        <RequirementItem key={req.id} rankId={rank.id} reqId={req.id} description={req.description} />
                    )) : <p className="p-4 text-text-secondary italic">No requirements have been defined for this rank yet.</p>}
                </div>
            )}
        </div>
    );
};

export const AdvancementPage: React.FC = () => {
    const { ranks } = useData();
    const { user } = useAuth();

    // Find the user's current rank object to get its sort order.
    // This is used to determine which ranks are "below" the user's current one.
    const userCurrentRank = user?.currentRankId 
        ? ranks.find(r => r.id === user.currentRankId) 
        : null;
    
    // Create a Set of completed requirement IDs for efficient lookup.
    const completedRequirementIds = new Set(user?.completedRequirements?.map(cr => cr.requirement_id) || []);

    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-text-primary mb-2">Rank Advancement</h1>
            <p className="text-lg text-text-secondary mb-6">Select a rank to view and complete its requirements.</p>
            <div>
                {ranks.map(rank => {
                    // A rank should be visually "completed" (crossed out) if either of two conditions are met:

                    // 1. The rank is of a lower order than the user's current rank.
                    //    (e.g., if user is First Class, then Scout and Tenderfoot are considered complete).
                    const isLowerRank = userCurrentRank ? rank.sort_order < userCurrentRank.sort_order : false;

                    // 2. The user has completed all requirements for that specific rank.
                    const allReqsForRankCompleted = rank.requirements.length > 0 && rank.requirements.every(req => completedRequirementIds.has(req.id));
                    
                    const isRankCompleted = isLowerRank || allReqsForRankCompleted;
                    
                    return <RankCard key={rank.id} rank={rank} isCompleted={isRankCompleted} />;
                })}
            </div>
        </div>
    );
};
