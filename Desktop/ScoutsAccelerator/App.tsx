

import React, { useState } from 'react';
import { HashRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { LandingPage } from './pages/LandingPage';
import { AdvancementPage } from './pages/AdvancementPage';
import { LessonPage } from './pages/LessonPage';
import { useData } from './hooks/useData';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { ProtectedRoute } from './components/ProtectedRoute';
import { OnboardingPage } from './pages/OnboardingPage';
import { DashboardPage } from './pages/DashboardPage';
import { QuizPage } from './pages/QuizPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { ScoutmasterDashboardPage } from './pages/ScoutmasterDashboardPage';
import SignOffsPage from './pages/SignOffsPage';

const CopyIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

const RlsErrorDisplay: React.FC<{ errorMessage: string }> = ({ errorMessage }) => {
  const policySql = `CREATE POLICY "Allow authenticated insert for ranks" ON public.ranks FOR INSERT TO authenticated WITH CHECK (true);`;
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(policySql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="max-w-3xl mx-auto my-10 bg-secondary p-8 rounded-xl border-2 border-red-500/50 shadow-2xl shadow-red-900/20">
      <h1 className="text-3xl font-bold text-red-300 flex items-center gap-3">
        <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        Database Configuration Required
      </h1>
      <p className="mt-4 text-text-secondary">
        The application can't start because it needs to set up the default scout ranks, but the database security rules are preventing it.
      </p>
      <p className="mt-2 text-text-secondary">
        This is a one-time setup step. To fix this, please run the following SQL command in your Supabase SQL Editor for this project.
      </p>
      <div className="mt-6">
        <p className="text-sm font-semibold text-text-primary mb-2">SQL Command to run:</p>
        <div className="bg-primary p-4 rounded-lg font-mono text-sm text-text-primary relative group">
          <pre><code>{policySql}</code></pre>
          <button onClick={copyToClipboard} className="absolute top-2 right-2 bg-border-color p-2 rounded-md text-text-secondary hover:text-text-primary transition-colors" aria-label="Copy SQL to clipboard">
            {copied ? 'Copied!' : <CopyIcon />}
          </button>
        </div>
      </div>
      <div className="mt-6 text-center">
        <button onClick={() => window.location.reload()} className="bg-accent text-white font-semibold py-2 px-6 rounded-lg hover:bg-accent-hover transition duration-300 shadow-[0_0_15px_theme(colors.accent/0.4)]">
          I've run the command, Refresh Page
        </button>
      </div>
      <p className="mt-8 text-xs text-text-secondary border-t border-border-color pt-4">
        <strong>Technical Details:</strong> {errorMessage}
      </p>
    </div>
  );
};


export const App: React.FC = () => {
  const { loading: dataLoading, error: dataError } = useData();

  // This spinner is for the initial global data fetch.
  // It doesn't use router hooks, so it can be outside the HashRouter.
  if (dataLoading) {
    return (
      <div className="flex justify-center items-center min-h-screen bg-primary">
        <div className="animate-spin rounded-full h-32 w-32 border-t-2 border-b-2 border-accent"></div>
      </div>
    );
  }
  
  // All other UI, including error states that use the Header, must be inside the router.
  return (
    <HashRouter>
      <div className="min-h-screen bg-primary font-sans">
        <Header />
        <main className="max-w-7xl mx-auto p-4 sm:p-6 lg:p-8 pb-24">
          {dataError && dataError.startsWith('Database setup error:') ? (
            // The RLS error is a special case that gets its own UI.
            <RlsErrorDisplay errorMessage={dataError} />
          ) : (
            // The main app UI with routes and generic errors.
            <>
              {dataError && (
                  <div className="bg-red-900/50 border border-red-500/30 text-red-200 p-4 mb-6 rounded-lg" role="alert">
                      <h2 className="font-bold text-white">Application Error</h2>
                      <p className="text-sm mt-1 text-red-300">Could not load application data. There might be an issue with the application's configuration or your browser's storage.</p>
                      <pre className="mt-2 text-xs whitespace-pre-wrap font-mono bg-black/30 p-2 rounded">{dataError}</pre>
                  </div>
              )}
              <Routes>
                {/* Public Routes */}
                <Route path="/login" element={<LoginPage />} />
                <Route path="/signup" element={<SignupPage />} />
                <Route path="/" element={<LandingPage />} />
                
                {/* Protected Routes */}
                <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
                <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
                <Route path="/advancement" element={<ProtectedRoute allowedRoles={['scout', 'admin']}><AdvancementPage /></ProtectedRoute>} />
                <Route path="/lesson/:rankId/:reqId" element={<ProtectedRoute><LessonPage /></ProtectedRoute>} />
                <Route path="/quiz/:rankId/:reqId" element={<ProtectedRoute><QuizPage /></ProtectedRoute>} />
                <Route path="/signoffs" element={<ProtectedRoute><SignOffsPage /></ProtectedRoute>} />
                
                {/* Role-Specific Routes */}
                <Route path="/admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboard /></ProtectedRoute>} />
                <Route path="/scoutmaster" element={<ProtectedRoute allowedRoles={['scoutmaster']}><ScoutmasterDashboardPage /></ProtectedRoute>} />

                {/* Catch-all redirects to the landing page */}
                <Route path="*" element={<Navigate to="/" />} />
              </Routes>
            </>
          )}
        </main>
      </div>
    </HashRouter>
  );
};
