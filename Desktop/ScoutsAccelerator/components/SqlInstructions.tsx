
import React, { useState } from 'react';

const CopyIcon: React.FC = () => (
  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
  </svg>
);

interface SqlInstructionsProps {
  title: string;
  description: string;
  sql: string;
}

export const SqlInstructions: React.FC<SqlInstructionsProps> = ({ title, description, sql }) => {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(sql).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  };

  return (
    <div className="bg-secondary p-6 sm:p-8 rounded-xl border-2 border-accent/30 shadow-2xl shadow-accent/10">
      <h2 className="text-2xl font-bold text-text-primary flex items-center gap-3">
        {title}
      </h2>
      <p className="mt-4 text-text-secondary">
        {description}
      </p>
      <div className="mt-6">
        <p className="text-sm font-semibold text-text-primary mb-2">SQL Commands to run in your Supabase SQL Editor:</p>
        <div className="bg-primary p-4 rounded-lg font-mono text-sm text-text-primary relative group max-h-[50vh] overflow-y-auto border border-border-color">
          <pre><code>{sql}</code></pre>
          <button onClick={copyToClipboard} className="absolute top-2 right-2 bg-border-color p-2 rounded-md text-text-secondary hover:text-text-primary transition-colors" aria-label="Copy SQL to clipboard">
            {copied ? 'Copied!' : <CopyIcon />}
          </button>
        </div>
      </div>
    </div>
  );
};
