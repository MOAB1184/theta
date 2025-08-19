

import React, { useState, useEffect } from 'react';
import { useAuth } from '../hooks/useAuth';
import { SignOffRequest, SignOffStatus } from '../types';

type Tab = 'incoming' | 'accepted' | 'history' | 'sent';

const SignOffsPage: React.FC = () => {
    const { 
        user, 
        isUserEligibleForSignOff, 
        getSignOffRequests,
        getUserById,
        acceptSignOffRequest, 
        updateSignOffStatus
    } = useAuth();
    
    const [eligible, setEligible] = useState(false);
    const [activeTab, setActiveTab] = useState<Tab>('incoming');
    const [requests, setRequests] = useState<SignOffRequest[]>([]);

    useEffect(() => {
        if (user) {
            const isEligible = isUserEligibleForSignOff(user);
            setEligible(isEligible);
            setActiveTab(isEligible ? 'incoming' : 'sent');
            if (user.troopId) {
                setRequests(getSignOffRequests(user.troopId));
            }
        }
    }, [user, getSignOffRequests, isUserEligibleForSignOff]);

    if (!user) return null;

    const getTabClass = (tabName: Tab) => {
        return activeTab === tabName 
            ? 'border-accent text-accent' 
            : 'border-transparent text-text-secondary hover:text-text-primary hover:border-gray-500';
    };

    const handleAccept = async (reqId: string) => {
        await acceptSignOffRequest(reqId);
    };

    const handleFinalize = async (reqId: string, status: 'approved' | 'rejected') => {
        await updateSignOffStatus(reqId, status);
    };

    const RequestItem: React.FC<{req: SignOffRequest, actions?: React.ReactNode}> = ({req, actions}) => (
        <div className="bg-secondary p-4 rounded-lg border border-border-color flex flex-col sm:flex-row justify-between sm:items-center gap-3">
            <div>
                <p className="font-bold text-text-primary">{req.scoutName}</p>
                <p className="text-sm text-text-secondary mt-1">{req.requirementDescription}</p>
                {req.status === 'accepted' && <p className="text-xs text-scout-blue font-semibold mt-1">Accepted by you</p>}
                {req.status === 'approved' && req.finalizedById === user.id && <p className="text-xs text-scout-green font-semibold mt-1">You approved this</p>}
                {req.status === 'rejected' && req.finalizedById === user.id && <p className="text-xs text-red-400 font-semibold mt-1">You rejected this</p>}
            </div>
            {actions && <div className="flex-shrink-0 flex gap-2">{actions}</div>}
        </div>
    );
    
    const SentRequestItem: React.FC<{req: SignOffRequest}> = ({req}) => {
        const getStatusPill = () => {
            switch(req.status){
                case 'pending': return <span className="text-xs font-semibold text-yellow-400 bg-yellow-900/50 px-2 py-1 rounded-full">Pending</span>
                case 'accepted': return <span className="text-xs font-semibold text-scout-blue bg-scout-blue/20 px-2 py-1 rounded-full">Accepted by {req.acceptedByName || 'leader'}</span>
                case 'approved': return <span className="text-xs font-semibold text-scout-green bg-scout-green/20 px-2 py-1 rounded-full">Approved by {req.finalizedByName || 'leader'}</span>
                case 'rejected': return <span className="text-xs font-semibold text-red-400 bg-red-900/50 px-2 py-1 rounded-full">Rejected by {req.finalizedByName || 'leader'}</span>
            }
        }
        
        return (
            <div className="bg-secondary p-4 rounded-lg border border-border-color flex justify-between items-center gap-3">
                <div>
                    <p className="font-bold text-text-primary">{req.requirementDescription}</p>
                </div>
                 <div className="flex-shrink-0">{getStatusPill()}</div>
            </div>
        );
    }
    
    const renderContent = () => {
        if (!user) return null;
        if (eligible) {
            // UI for Scoutmasters and eligible scouts
            const incoming = requests.filter(r => r.status === 'pending');
            const accepted = requests.filter(r => r.status === 'accepted' && r.acceptedById === user.id);
            const history = requests.filter(r => (r.status === 'approved' || r.status === 'rejected') && r.finalizedById === user.id);
            
            return (
                <>
                    {activeTab === 'incoming' && (
                        <div className="space-y-4">
                            {incoming.length > 0 ? incoming.map(req => (
                                <RequestItem key={req.id} req={req} actions={
                                    <button onClick={() => handleAccept(req.id)} className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white hover:bg-accent-hover">Accept</button>
                                }/>
                            )) : <p className="text-center text-text-secondary italic py-8">No incoming requests.</p>}
                        </div>
                    )}
                     {activeTab === 'accepted' && (
                        <div className="space-y-4">
                            {accepted.length > 0 ? accepted.map(req => (
                                <RequestItem key={req.id} req={req} actions={<>
                                    <button onClick={() => handleFinalize(req.id, 'approved')} className="rounded-md bg-scout-green/20 px-3 py-1.5 text-sm font-semibold text-scout-green hover:bg-scout-green/30">Passed Check-in</button>
                                    <button onClick={() => handleFinalize(req.id, 'rejected')} className="rounded-md bg-red-500/20 px-3 py-1.5 text-sm font-semibold text-red-400 hover:bg-red-500/30">Failed Check-in</button>
                                </>}/>
                            )) : <p className="text-center text-text-secondary italic py-8">You have not accepted any requests.</p>}
                        </div>
                    )}
                    {activeTab === 'history' && (
                         <div className="space-y-4">
                            {history.length > 0 ? history.map(req => (
                                <RequestItem key={req.id} req={req}/>
                            )) : <p className="text-center text-text-secondary italic py-8">No sign-off history yet.</p>}
                        </div>
                    )}
                </>
            );
        } else {
            // UI for non-eligible scouts
            const sent = requests.filter(r => r.scoutId === user.id && (r.status === 'pending' || r.status === 'accepted'));
            const history = requests.filter(r => r.scoutId === user.id && (r.status === 'approved' || r.status === 'rejected'));
            return (
                <>
                    {activeTab === 'sent' && (
                         <div className="space-y-4">
                            {sent.length > 0 ? sent.map(req => (
                                <SentRequestItem key={req.id} req={req} />
                            )) : <p className="text-center text-text-secondary italic py-8">You have no active requests.</p>}
                        </div>
                    )}
                     {activeTab === 'history' && (
                         <div className="space-y-4">
                            {history.length > 0 ? history.map(req => (
                                <SentRequestItem key={req.id} req={req} />
                            )) : <p className="text-center text-text-secondary italic py-8">No past sign-offs.</p>}
                        </div>
                    )}
                </>
            );
        }
    };

    return (
        <div className="max-w-4xl mx-auto">
            <h1 className="text-3xl font-bold text-text-primary mb-2">Sign-offs</h1>
            <p className="text-lg text-text-secondary mb-6">Manage all advancement sign-off activity here.</p>
            
            <div className="border-b border-border-color mb-6">
                <nav className="-mb-px flex space-x-6" aria-label="Tabs">
                    {eligible ? (
                        <>
                            <button onClick={() => setActiveTab('incoming')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${getTabClass('incoming')}`}>Incoming Requests</button>
                            <button onClick={() => setActiveTab('accepted')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${getTabClass('accepted')}`}>My Accepted Requests</button>
                            <button onClick={() => setActiveTab('history')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${getTabClass('history')}`}>Sign-off History</button>
                        </>
                    ) : (
                         <>
                            <button onClick={() => setActiveTab('sent')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${getTabClass('sent')}`}>My Requests</button>
                            <button onClick={() => setActiveTab('history')} className={`whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm transition-colors ${getTabClass('history')}`}>Past Sign-offs</button>
                        </>
                    )}
                </nav>
            </div>
            
            <div>{renderContent()}</div>
        </div>
    );
};

export default SignOffsPage;
