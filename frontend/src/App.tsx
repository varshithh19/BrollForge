import React, { useState } from 'react';
import { Navbar } from './components/Navbar';
import { DashboardPage } from './pages/DashboardPage';
import { CreateVideoPage } from './pages/CreateVideoPage';
import { JobDetailsPage } from './pages/JobDetailsPage';

export const App: React.FC = () => {
  const [currentView, setCurrentView] = useState<'dashboard' | 'create' | 'job'>('dashboard');
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  const handleNavigate = (view: string, jobId?: string) => {
    if (view === 'job' && jobId) {
      setSelectedJobId(jobId);
      setCurrentView('job');
    } else if (view === 'create') {
      setCurrentView('create');
    } else {
      setCurrentView('dashboard');
    }
  };

  const handleJobCreated = (jobId: string) => {
    setSelectedJobId(jobId);
    setCurrentView('job');
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col text-slate-100">
      <Navbar currentView={currentView} onNavigate={handleNavigate} />
      <main className="flex-1">
        {currentView === 'dashboard' && <DashboardPage onNavigate={handleNavigate} />}
        {currentView === 'create' && (
          <CreateVideoPage
            onJobCreated={handleJobCreated}
            onCancel={() => setCurrentView('dashboard')}
          />
        )}
        {currentView === 'job' && selectedJobId && (
          <JobDetailsPage jobId={selectedJobId} onBack={() => setCurrentView('dashboard')} />
        )}
      </main>
      <footer className="border-t border-slate-900 bg-slate-950 py-6 text-center text-xs text-slate-500">
        <p>BrollForge — IncuBrix PS3: Script and Voiceover to B-roll Video Engine</p>
      </footer>
    </div>
  );
};
