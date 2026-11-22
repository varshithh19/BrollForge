import React, { useEffect, useState } from 'react';
import {
  Film,
  Download,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Clock,
  Layers,
  FileText,
  Sliders,
  ExternalLink,
  ShieldCheck,
  Sparkles,
  ArrowLeft,
  Video,
} from 'lucide-react';
import { api } from '../services/api';
import { Job, TimelineData, TimelineScene } from '../types';

interface JobDetailsPageProps {
  jobId: string;
  onBack: () => void;
}

export const JobDetailsPage: React.FC<JobDetailsPageProps> = ({ jobId, onBack }) => {
  const [job, setJob] = useState<Job | null>(null);
  const [timeline, setTimeline] = useState<TimelineData | null>(null);
  const [activeRatio, setActiveRatio] = useState<string>('16:9');
  const [loading, setLoading] = useState(true);
  const [swappingSceneId, setSwappingSceneId] = useState<string | null>(null);
  const [newHintInput, setNewHintInput] = useState<string>('');

  const fetchJobData = async () => {
    try {
      const j = await api.getJob(jobId);
      setJob(j);

      // If finished, load timeline
      if (j.status === 'succeeded' && !timeline) {
        try {
          const tl = await api.getTimeline(jobId);
          setTimeline(tl);
          if (tl.aspect_ratios && tl.aspect_ratios.length > 0) {
            setActiveRatio(tl.aspect_ratios[0]);
          }
        } catch (e) {
          console.error('Could not load timeline', e);
        }
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobData();
    const interval = setInterval(() => {
      if (job?.status === 'queued' || job?.status === 'running') {
        fetchJobData();
      }
    }, 2500);
    return () => clearInterval(interval);
  }, [jobId, job?.status]);

  const handleSwapClip = async (sceneId: string) => {
    setSwappingSceneId(sceneId);
    try {
      await api.swapSceneClip(jobId, sceneId, newHintInput.trim() || undefined);
      // Reload job and timeline
      const j = await api.getJob(jobId);
      setJob(j);
      const tl = await api.getTimeline(jobId);
      setTimeline(tl);
      setNewHintInput('');
    } catch (err: any) {
      alert(`Clip swap failed: ${err.message}`);
    } finally {
      setSwappingSceneId(null);
    }
  };

  if (loading && !job) {
    return (
      <div className="max-w-6xl mx-auto px-4 py-16 text-center text-slate-400">
        <RefreshCw className="w-8 h-8 animate-spin mx-auto text-indigo-500 mb-3" />
        <p>Loading job information...</p>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="max-w-4xl mx-auto px-4 py-16 text-center text-slate-400">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h2 className="text-xl font-bold text-white">Job Not Found</h2>
        <p className="mt-1">Could not locate job with ID {jobId}</p>
        <button onClick={onBack} className="mt-4 px-4 py-2 bg-slate-800 text-white rounded-lg">
          Back to Dashboard
        </button>
      </div>
    );
  }

  const videos = job.result_links?.videos || {};
  const currentVideo = videos[activeRatio];

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <button
            onClick={onBack}
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-2xl font-bold text-white tracking-tight">Job {job.job_id.slice(0, 8)}...</h1>
              {job.status === 'succeeded' && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-950 text-emerald-400 border border-emerald-800">
                  Completed
                </span>
              )}
              {job.status === 'running' && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-950 text-indigo-400 border border-indigo-800 animate-pulse">
                  Processing ({job.progress}%)
                </span>
              )}
              {job.status === 'failed' && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-950 text-rose-400 border border-rose-800">
                  Failed
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">ID: {job.job_id}</p>
          </div>
        </div>

        {/* Action Downloads */}
        {job.status === 'succeeded' && (
          <div className="flex flex-wrap gap-2">
            {job.result_links?.timeline && (
              <a
                href={job.result_links.timeline}
                download
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs transition"
              >
                <FileText className="w-3.5 h-3.5 text-indigo-400" />
                <span>timeline.json</span>
              </a>
            )}
            {job.result_links?.manifest && (
              <a
                href={job.result_links.manifest}
                download
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs transition"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                <span>manifest.json</span>
              </a>
            )}
            {job.result_links?.captions_srt && (
              <a
                href={job.result_links.captions_srt}
                download
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white text-xs transition"
              >
                <Download className="w-3.5 h-3.5 text-amber-400" />
                <span>captions.srt</span>
              </a>
            )}
          </div>
        )}
      </div>

      {/* Progress & Stage Banner */}
      {(job.status === 'running' || job.status === 'queued') && (
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-4">
          <div className="flex items-center justify-between text-sm">
            <span className="font-semibold text-white flex items-center space-x-2">
              <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
              <span>Current Stage: {job.stage || 'queued'}</span>
            </span>
            <span className="font-mono text-indigo-400 font-bold">{job.progress}%</span>
          </div>
          <div className="w-full bg-slate-950 rounded-full h-3 overflow-hidden p-0.5 border border-slate-800">
            <div
              className="bg-indigo-600 h-2 rounded-full transition-all duration-500 shadow-md shadow-indigo-500/50"
              style={{ width: `${Math.max(5, job.progress)}%` }}
            />
          </div>
          <p className="text-xs text-slate-500">
            Pipeline executes asynchronously. Video rendering, audio mixing, and caption alignment in progress.
          </p>
        </div>
      )}

      {/* Error Card */}
      {job.error && (
        <div className="bg-rose-950/30 border border-rose-900/60 rounded-2xl p-6 text-rose-300 space-y-2">
          <div className="flex items-center space-x-2 font-bold text-rose-400">
            <AlertTriangle className="w-5 h-5" />
            <span>Error: {job.error.code}</span>
          </div>
          <p className="text-sm">{job.error.message}</p>
        </div>
      )}

      {/* Completed Results: Video Player & Aspect Ratio Selector */}
      {job.status === 'succeeded' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
          {/* Video Preview Player Column */}
          <div className="lg:col-span-7 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-white flex items-center space-x-2">
                <Video className="w-5 h-5 text-indigo-400" />
                <span>Rendered Video Preview</span>
              </h2>

              {/* Ratio Tabs */}
              <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-xl">
                {Object.keys(videos).map((ratio) => (
                  <button
                    key={ratio}
                    onClick={() => setActiveRatio(ratio)}
                    className={`px-3 py-1 rounded-lg text-xs font-mono font-medium transition ${
                      activeRatio === ratio ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {ratio}
                  </button>
                ))}
              </div>
            </div>

            {/* Video Canvas Container */}
            <div className="bg-slate-950 border border-slate-800 rounded-2xl p-4 flex items-center justify-center min-h-[420px] shadow-2xl relative">
              {currentVideo ? (
                <div
                  className={`w-full flex justify-center items-center ${
                    activeRatio === '9:16' ? 'max-w-xs' : activeRatio === '1:1' ? 'max-w-md' : 'max-w-2xl'
                  }`}
                >
                  <video
                    key={currentVideo.url}
                    controls
                    autoPlay
                    loop
                    className="rounded-xl shadow-lg border border-slate-800 w-full"
                    src={currentVideo.url}
                  />
                </div>
              ) : (
                <div className="text-slate-500 text-sm">No preview available for ratio {activeRatio}</div>
              )}
            </div>

            {/* Video File Metrics */}
            {currentVideo && (
              <div className="grid grid-cols-4 gap-2 text-center text-xs">
                <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-slate-500 block">Resolution</span>
                  <span className="font-semibold text-white">
                    {currentVideo.width}x{currentVideo.height}
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-slate-500 block">Duration</span>
                  <span className="font-semibold text-white">{currentVideo.duration}s</span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-slate-500 block">File Size</span>
                  <span className="font-semibold text-white">
                    {(currentVideo.file_size / (1024 * 1024)).toFixed(2)} MB
                  </span>
                </div>
                <div className="bg-slate-900 p-2.5 rounded-xl border border-slate-800">
                  <span className="text-slate-500 block">Codec</span>
                  <span className="font-semibold text-white">H.264 / AAC</span>
                </div>
              </div>
            )}

            {currentVideo && (
              <a
                href={currentVideo.url}
                download
                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-medium rounded-xl flex items-center justify-center space-x-2 shadow-lg shadow-indigo-600/20 transition"
              >
                <Download className="w-4 h-4" />
                <span>Download {activeRatio} Video</span>
              </a>
            )}
          </div>

          {/* Scene Breakdown & Clip Swapper Column */}
          <div className="lg:col-span-5 space-y-4">
            <h2 className="text-lg font-bold text-white flex items-center space-x-2">
              <Layers className="w-5 h-5 text-indigo-400" />
              <span>Scene Timeline ({timeline?.scenes?.length || 0})</span>
            </h2>

            <div className="space-y-3 max-h-[560px] overflow-y-auto pr-1">
              {timeline?.scenes?.map((sc: TimelineScene) => (
                <div
                  key={sc.scene_id}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-2.5 hover:border-slate-700 transition"
                >
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-mono text-indigo-400 font-semibold">
                      Scene {sc.scene_index + 1} ({sc.start_time}s - {sc.end_time}s)
                    </span>
                    <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-900/60 font-medium">
                      Score: {sc.relevance_score}/5.0
                    </span>
                  </div>

                  <p className="text-sm font-medium text-slate-100 italic">"{sc.text}"</p>

                  <div className="text-xs text-slate-400 space-y-1 bg-slate-950 p-2.5 rounded-lg border border-slate-800/80">
                    <div>
                      <span className="text-slate-500">Query: </span>
                      <span className="text-slate-300 font-mono">{sc.search_query}</span>
                    </div>
                    {sc.visual_hint && (
                      <div>
                        <span className="text-indigo-400">Visual Hint: </span>
                        <span className="text-indigo-300">{sc.visual_hint}</span>
                      </div>
                    )}
                    <div>
                      <span className="text-slate-500">Source: </span>
                      <span className="text-slate-300 capitalize">{sc.provider || 'local'}</span> ({sc.licence_name})
                    </div>
                    <div className="text-slate-500 text-[11px] truncate">
                      {sc.attribution}
                    </div>
                  </div>

                  {/* Clip Swapping Form */}
                  <div className="pt-1 flex gap-2">
                    <input
                      type="text"
                      placeholder="New visual hint for swap..."
                      value={swappingSceneId === sc.scene_id ? newHintInput : ''}
                      onChange={(e) => {
                        setSwappingSceneId(sc.scene_id);
                        setNewHintInput(e.target.value);
                      }}
                      className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-100 placeholder-slate-600"
                    />
                    <button
                      type="button"
                      disabled={swappingSceneId === sc.scene_id}
                      onClick={() => handleSwapClip(sc.scene_id)}
                      className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 text-xs font-medium rounded-lg border border-slate-700 transition"
                    >
                      {swappingSceneId === sc.scene_id ? 'Swapping...' : 'Swap Clip'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
