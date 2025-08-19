
import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useData } from '../hooks/useData';

export const LessonPage: React.FC = () => {
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

  return (
    <div className="max-w-4xl mx-auto">
      <Link to="/advancement" className="text-accent hover:underline mb-4 inline-block font-semibold">&larr; Back to Advancement</Link>
      <div className="bg-secondary p-6 sm:p-8 rounded-xl border border-border-color">
        <h1 className="text-3xl font-bold text-text-primary">{requirement.description}</h1>
        <p className="text-lg text-text-secondary mb-6">Part of the <span className="font-semibold">{rank.name}</span> rank</p>
        
        <div 
          className="prose prose-lg max-w-none prose-invert prose-h1:text-accent prose-img:rounded-md prose-p:text-text-secondary prose-strong:text-text-primary prose-a:text-accent"
          dangerouslySetInnerHTML={{ __html: (requirement.lesson_content as { html: string })?.html || '' }} 
        />
      </div>
    </div>
  );
};
