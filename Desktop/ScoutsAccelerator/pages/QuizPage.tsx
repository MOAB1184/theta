

import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useData } from '../hooks/useData';

export const QuizPage: React.FC = () => {
  const { rankId, reqId } = useParams();
  const { ranks } = useData();

  const rank = ranks.find(r => r.id === rankId);
  const requirement = rank?.requirements.find(r => r.id === reqId);

  if (!rank || !requirement) {
    return (
        <div className="text-center">
            <h1 className="text-2xl font-bold">Requirement not found</h1>
            <Link to="/advancement" className="text-accent hover:underline">Back to Advancement</Link>
        </div>
    );
  }

  const lessonContent = (requirement.lesson_content as { html: string })?.html || 'No lesson content available.';
  
  return (
    <div className="max-w-4xl mx-auto p-6">
      <Link to="/advancement" className="text-accent hover:underline mb-6 inline-block font-semibold">&larr; Back to Advancement</Link>
      
      <div className="bg-secondary border border-border-color rounded-xl p-6 shadow-lg">
        <h1 className="text-3xl font-bold text-text-primary mb-4">{requirement.description}</h1>
        
        <div className="prose prose-invert max-w-none">
          <div 
            className="text-text-primary leading-relaxed"
            dangerouslySetInnerHTML={{ __html: lessonContent }}
          />
        </div>
        
        <div className="mt-8 pt-6 border-t border-border-color">
          <h2 className="text-xl font-semibold text-text-primary mb-4">Ready to test your knowledge?</h2>
          <p className="text-text-secondary mb-4">
            Review the lesson content above. When you're confident you understand the material, 
            you can request a sign-off from your Scoutmaster.
          </p>
          <Link 
            to={`/signoffs/${rankId}/${reqId}`}
            className="inline-flex items-center px-6 py-3 bg-accent hover:bg-accent-hover text-white font-semibold rounded-lg transition-colors duration-200"
          >
            Request Sign-Off
            <svg className="ml-2 w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      </div>
    </div>
  );
};