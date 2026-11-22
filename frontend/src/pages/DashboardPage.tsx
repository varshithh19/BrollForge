import React, { useEffect, useState } from 'react';
import { Film, Play, AlertTriangle, Clock, Plus, RefreshCw, CheckCircle2, ChevronRight, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import { Job } from '../types';

interface DashboardPageProps {
  onNavigate: (view: string, jobId?: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchJobs = async () => {
    try {
      const data = await api.getJobs(30);
      setJobs(data.jobs || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 4000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Hero Banner */}
      <div className="bg-gradient-to-r from-slate-900 via-indigo-950/40 to-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 shadow-xl">
        <div className="max-w-3xl space-y-3">
          <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/30 text-indigo-400 text-xs font-semibold uppercase tracking-wider">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Automated B-Roll Engine — IncuBrix PS3</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            Script and Voiceover to B-roll Video
          </h1>
          <p className="text-slate-300 text-base leading-relaxed">
            Generate license-clean, multi-aspect-ratio B-roll videos synchronized to voice timing.
            Every scene is derived through meaning-based segmentation, backed by verifiable commercial-use stock footage and intelligent deduplication.
          </p>
          <div className="pt-2 flex flex-wrap gap-3">
            <button
              onClick={() => onNavigate('create')}
              className="inline-flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white font-medium px-5 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 transition transform active:scale-95"
            >
              <Plus className="w-5 h-5" />
              <span>Create Video</span>
            </button>
            <button
              onClick={() => {
                setRefreshing(true);
                fetchJobs();
              }}
              className="inline-flex items-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2.5 rounded-xl border border-slate-700 transition"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>
          </div>
        </div>
      </div>

      {/* Recent Jobs Header */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold text-white flex items-center space-x-2">
            <Film className="w-5 h-5 text-indigo-400" />
            <span>Recent Generation Jobs</span>
          </h2>
          <span className="text-sm text-slate-400">{jobs.length} jobs on record</span>
        </div>

        {loading ? (
          <div className="text-center py-16 text-slate-500">Loading jobs...</div>
        ) : jobs.length === 0 ? (
          <div className="border border-dashed border-slate-800 rounded-2xl p-12 text-center space-y-3">
            <Film className="w-10 h-10 text-slate-600 mx-auto" />
            <h3 className="text-slate-300 font-semibold text-lg">No generation jobs yet</h3>
            <p className="text-slate-500 text-sm max-w-sm mx-auto">
              Get started by uploading an audio voiceover or typing a script to produce your first video.
            </p>
            <button
              onClick={() => onNavigate('create')}
              className="mt-2 inline-flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium px-4 py-2 rounded-lg transition"
            >
              <Plus className="w-4 h-4" />
              <span>Create Your First Video</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-4">
            {jobs.map((job) => (
              <div
                key={job.job_id}
                onClick={() => onNavigate('job', job.job_id)}
                className="bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl p-5 transition cursor-pointer flex flex-col md:flex-row md:items-center justify-between gap-4 group hover:shadow-lg"
              >
                <div className="space-y-2 flex-1">
                  <div className="flex items-center space-x-3">
                    <span className="font-mono text-sm font-semibold text-white group-hover:text-indigo-400 transition">
                      {job.job_id.slice(0, 13)}...
                    </span>
                    <span className="text-xs uppercase px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                      {job.input_type || 'script'}
                    </span>
                    <span className="text-xs text-slate-400 flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1" />
                      {new Date(job.created_at).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="flex items-center space-x-2 text-xs text-slate-400">
                    <span>Aspect Ratios:</span>
                    {(job.aspect_ratios || ['16:9']).map((r) => (
                      <span key={r} className="px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700/80 font-mono">
                        {r}
                      </span>
                    ))}
                  </div>

                  {job.error && (
                    <div className="text-xs text-rose-400 flex items-center space-x-1.5 bg-rose-950/30 p-2 rounded border border-rose-900/50">
                      <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                      <span>{job.error.message || 'Job execution error'}</span>
                    </div>
                  )}
                </div>

                <div className="flex items-center space-x-4">
                  {/* Status Badge */}
                  <div className="text-right">
                    <div className="flex items-center justify-end space-x-1.5">
                      {job.status === 'succeeded' && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800/60">
                          <CheckCircle2 className="w-3.5 h-3.5 mr-1" /> Complete
                        </span>
                      )}
                      {job.status === 'running' && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-950 text-indigo-400 border border-indigo-800/60">
                          <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> {job.stage || 'Rendering'} ({job.progress}%)
                        </span>
                      )}
                      {job.status === 'queued' && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-950 text-amber-400 border border-amber-800/60">
                          Queued
                        </span>
                      )}
                      {job.status === 'failed' && (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950 text-rose-400 border border-rose-800/60">
                          Failed
                        </span>
                      )}
                    </div>
                    {job.status === 'running' && (
                      <div className="w-32 bg-slate-800 rounded-full h-1.5 mt-2 overflow-hidden">
                        <div
                          className="bg-indigo-500 h-1.5 rounded-full transition-all duration-300"
                          style={{ width: `${job.progress}%` }}
                        />
                      </div>
                    )}
                  </div>

                  <ChevronRight className="w-5 h-5 text-slate-600 group-hover:text-slate-300 transition transform group-hover:translate-x-1" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
