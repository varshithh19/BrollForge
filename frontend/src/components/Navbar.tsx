import React, { useEffect, useState } from 'react';
import { Video, Film, CheckCircle, AlertCircle, PlusCircle, ShieldCheck } from 'lucide-react';
import { api } from '../services/api';

interface NavbarProps {
  currentView: string;
  onNavigate: (view: string, jobId?: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const [isReady, setIsReady] = useState<boolean | null>(null);

  useEffect(() => {
    api.getReady()
      .then((data) => setIsReady(data.status === 'ready'))
      .catch(() => setIsReady(false));
  }, []);

  return (
    <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3 cursor-pointer" onClick={() => onNavigate('dashboard')}>
          <div className="bg-indigo-600 p-2 rounded-lg text-white shadow-lg shadow-indigo-500/20">
            <Film className="w-5 h-5" />
          </div>
          <div>
            <span className="font-bold text-lg text-white tracking-tight">BrollForge</span>
            <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded bg-indigo-900/60 text-indigo-300 border border-indigo-700/50">
              v1.0 Engine
            </span>
          </div>
        </div>

        <nav className="flex items-center space-x-2 sm:space-x-4">
          <button
            onClick={() => onNavigate('dashboard')}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition ${
              currentView === 'dashboard'
                ? 'bg-slate-800 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50'
            }`}
          >
            Dashboard
          </button>
          <button
            onClick={() => onNavigate('create')}
            className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition ${
              currentView === 'create'
                ? 'bg-indigo-600 text-white'
                : 'bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/30'
            }`}
          >
            <PlusCircle className="w-4 h-4" />
            <span>Create Video</span>
          </button>

          <div className="flex items-center space-x-1.5 pl-4 border-l border-slate-800 text-xs">
            {isReady === true ? (
              <span className="flex items-center text-emerald-400 font-medium">
                <CheckCircle className="w-3.5 h-3.5 mr-1" /> Ready
              </span>
            ) : isReady === false ? (
              <span className="flex items-center text-amber-400 font-medium">
                <AlertCircle className="w-3.5 h-3.5 mr-1" /> Initializing
              </span>
            ) : (
              <span className="text-slate-500">Checking...</span>
            )}
          </div>
        </nav>
      </div>
    </header>
  );
};
