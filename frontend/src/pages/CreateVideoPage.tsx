import React, { useState } from 'react';
import { Upload, FileText, CheckSquare, Settings2, Sliders, AlertCircle, ArrowRight, Plus, Trash2, Mic } from 'lucide-react';
import { api } from '../services/api';
import { CreateJobPayload, SceneInput } from '../types';

interface CreateVideoPageProps {
  onJobCreated: (jobId: string) => void;
  onCancel: () => void;
}

export const CreateVideoPage: React.FC<CreateVideoPageProps> = ({ onJobCreated, onCancel }) => {
  const [mode, setMode] = useState<'script' | 'upload' | 'scenes'>('script');

  // Mode 1: Upload
  const [audioFile, setAudioFile] = useState<File | null>(null);

  // Mode 2: Script
  const [scriptText, setScriptText] = useState(
    "Trust is earned slowly. Sales grew 40% in 2025 as modern teams embraced cloud computing and intelligent automation."
  );
  const [voice, setVoice] = useState('en-IN-female');

  // Mode 3: Structured IncuBrix Scenes
  const [scenes, setScenes] = useState<SceneInput[]>([
    { text: "Trust is earned slowly.", visual_hint: "two business partners shaking hands in modern office" },
    { text: "Sales grew 40% in 2025.", visual_hint: "team reviewing positive financial analytics chart" },
    { text: "Cloud computing powers modern software automation.", visual_hint: "data center server rack with flashing blue lights" },
  ]);

  // Video Configuration
  const [aspectRatios, setAspectRatios] = useState<string[]>(['16:9', '9:16']);
  const [style, setStyle] = useState('bright, modern, real-world footage');
  const [avoidList, setAvoidList] = useState<string[]>([
    "people's faces",
    "alcohol",
    "violence",
    "logos",
  ]);
  const [avoidInput, setAvoidInput] = useState('');
  const [burnCaptions, setBurnCaptions] = useState(true);
  const [generateSrt, setGenerateSrt] = useState(true);

  // State
  const [submitting, setSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const toggleAspectRatio = (ratio: string) => {
    if (aspectRatios.includes(ratio)) {
      if (aspectRatios.length === 1) return; // Keep at least one
      setAspectRatios(aspectRatios.filter((r) => r !== ratio));
    } else {
      setAspectRatios([...aspectRatios, ratio]);
    }
  };

  const addAvoidTerm = () => {
    if (avoidInput.trim() && !avoidList.includes(avoidInput.trim())) {
      setAvoidList([...avoidList, avoidInput.trim()]);
      setAvoidInput('');
    }
  };

  const removeAvoidTerm = (term: string) => {
    setAvoidList(avoidList.filter((t) => t !== term));
  };

  const addSceneRow = () => {
    setScenes([...scenes, { text: '', visual_hint: '' }]);
  };

  const removeSceneRow = (index: number) => {
    setScenes(scenes.filter((_, i) => i !== index));
  };

  const updateSceneRow = (index: number, field: 'text' | 'visual_hint', value: string) => {
    const updated = [...scenes];
    updated[index][field] = value;
    setScenes(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);
    setSubmitting(true);

    try {
      const idempotencyKey = `broll-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

      if (mode === 'upload') {
        if (!audioFile) {
          throw new Error('Please select an audio file (MP3, WAV, or M4A).');
        }
        const formData = new FormData();
        formData.append('file', audioFile);
        formData.append('aspect_ratios', JSON.stringify(aspectRatios));
        formData.append('style', style);
        formData.append('avoid', JSON.stringify(avoidList));
        formData.append('burn_captions', String(burnCaptions));

        const job = await api.uploadAudioJob(formData, idempotencyKey);
        onJobCreated(job.job_id);
      } else {
        const payload: CreateJobPayload = {
          aspect_ratios: aspectRatios,
          style,
          avoid: avoidList,
          captions: { burn_in: burnCaptions, srt: generateSrt },
        };

        if (mode === 'script') {
          if (!scriptText.trim()) throw new Error('Script text cannot be empty.');
          payload.script = scriptText.trim();
          payload.voice = voice;
        } else if (mode === 'scenes') {
          const validScenes = scenes.filter((s) => s.text.trim());
          if (validScenes.length === 0) throw new Error('Please add at least one scene with narration.');
          payload.scenes = validScenes;
          payload.voice = voice;
        }

        const job = await api.createJob(payload, idempotencyKey);
        onJobCreated(job.job_id);
      }
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to submit generation job');
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-8 space-y-8">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">Create B-Roll Video</h1>
        <p className="text-slate-400 text-sm mt-1">
          Configure narration, style guidelines, and output aspect ratios to generate your video.
        </p>
      </div>

      {errorMsg && (
        <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-900/60 text-rose-300 text-sm flex items-center space-x-3">
          <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-400" />
          <span>{errorMsg}</span>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Input Mode Selector */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-1.5 flex space-x-1">
          <button
            type="button"
            onClick={() => setMode('script')}
            className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2 ${
              mode === 'script' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <FileText className="w-4 h-4" />
            <span>Enter Script (TTS)</span>
          </button>
          <button
            type="button"
            onClick={() => setMode('upload')}
            className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2 ${
              mode === 'upload' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Upload className="w-4 h-4" />
            <span>Upload Voiceover</span>
          </button>
          <button
            type="button"
            onClick={() => setMode('scenes')}
            className={`flex-1 py-2.5 px-3 rounded-lg text-sm font-medium transition flex items-center justify-center space-x-2 ${
              mode === 'scenes' ? 'bg-indigo-600 text-white shadow' : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sliders className="w-4 h-4" />
            <span>IncuBrix Scene List</span>
          </button>
        </div>

        {/* Input Form Fields */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
          {mode === 'script' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1.5">Narration Script</label>
                <textarea
                  rows={5}
                  value={scriptText}
                  onChange={(e) => setScriptText(e.target.value)}
                  placeholder="Enter the full voiceover narration text here..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 text-sm"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1.5">Voice Persona</label>
                <select
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-100 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                >
                  <option value="en-IN-female">Indian English (Female - NeerjaNeural) [Default]</option>
                  <option value="en-IN-male">Indian English (Male - PrabhatNeural)</option>
                  <option value="en-US-female">US English (Female - AriaNeural)</option>
                  <option value="en-US-male">US English (Male - GuyNeural)</option>
                  <option value="hi-IN-female">Hindi (Female - SwaraNeural)</option>
                  <option value="ta-IN-female">Tamil (Female - PallaviNeural)</option>
                </select>
              </div>
            </div>
          )}

          {mode === 'upload' && (
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-200 mb-1.5">
                  Voiceover Audio File (MP3, WAV, or M4A, max 10 minutes)
                </label>
                <input
                  type="file"
                  accept=".mp3,.wav,.m4a,audio/*"
                  onChange={(e) => setAudioFile(e.target.files?.[0] || null)}
                  className="block w-full text-sm text-slate-400 file:mr-4 file:py-2.5 file:px-4 file:rounded-xl file:border-0 file:text-sm file:font-semibold file:bg-indigo-600 file:text-white hover:file:bg-indigo-500 cursor-pointer border border-slate-800 rounded-xl bg-slate-950 p-2"
                  required
                />
              </div>
              {audioFile && (
                <div className="text-xs text-slate-400 flex items-center space-x-2">
                  <Mic className="w-4 h-4 text-indigo-400" />
                  <span>
                    Selected: <strong>{audioFile.name}</strong> ({(audioFile.size / (1024 * 1024)).toFixed(2)} MB)
                  </span>
                </div>
              )}
            </div>
          )}

          {mode === 'scenes' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-slate-200">
                  Structured Scene Breakdown with Visual Hints
                </label>
                <button
                  type="button"
                  onClick={addSceneRow}
                  className="inline-flex items-center space-x-1 text-xs text-indigo-400 hover:text-indigo-300"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Scene</span>
                </button>
              </div>

              <div className="space-y-3">
                {scenes.map((sc, idx) => (
                  <div key={idx} className="flex gap-2 items-start bg-slate-950 p-3 rounded-xl border border-slate-800">
                    <span className="text-xs font-mono text-slate-500 mt-2.5 w-6 text-center">{idx + 1}</span>
                    <div className="flex-1 space-y-2">
                      <input
                        type="text"
                        value={sc.text}
                        onChange={(e) => updateSceneRow(idx, 'text', e.target.value)}
                        placeholder="Narration phrase or sentence..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-slate-100"
                      />
                      <input
                        type="text"
                        value={sc.visual_hint || ''}
                        onChange={(e) => updateSceneRow(idx, 'visual_hint', e.target.value)}
                        placeholder="Visual hint (e.g. data center server rack with blue LEDs)..."
                        className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2 text-xs text-indigo-300 placeholder-slate-600"
                      />
                    </div>
                    {scenes.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeSceneRow(idx)}
                        className="text-slate-600 hover:text-rose-400 p-2"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Video Configurations */}
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 space-y-6">
          <h2 className="text-base font-bold text-white flex items-center space-x-2">
            <Settings2 className="w-4 h-4 text-indigo-400" />
            <span>Video & Rendering Configuration</span>
          </h2>

          {/* Aspect Ratios */}
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-2">
              Target Aspect Ratios (Outputs will be generated for all selected)
            </label>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: '16:9', name: 'Landscape (16:9)', desc: '1920x1080 (YouTube/Desktop)' },
                { id: '9:16', name: 'Vertical (9:16)', desc: '1080x1920 (Reels/TikTok)' },
                { id: '1:1', name: 'Square (1:1)', desc: '1080x1080 (Instagram/Feed)' },
              ].map((item) => (
                <div
                  key={item.id}
                  onClick={() => toggleAspectRatio(item.id)}
                  className={`p-3 rounded-xl border cursor-pointer transition flex flex-col justify-between ${
                    aspectRatios.includes(item.id)
                      ? 'bg-indigo-950/40 border-indigo-500 text-white shadow-sm'
                      : 'bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-semibold text-sm">{item.name}</span>
                    <input
                      type="checkbox"
                      checked={aspectRatios.includes(item.id)}
                      readOnly
                      className="rounded text-indigo-600 focus:ring-0"
                    />
                  </div>
                  <span className="text-xs text-slate-500 mt-2 font-mono">{item.desc}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Style Prompt */}
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1.5">Visual Style Prompt</label>
            <input
              type="text"
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-slate-100"
            />
          </div>

          {/* Avoid List */}
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1.5">
              Avoid List (Safety and Visual Constraints)
            </label>
            <div className="flex gap-2 mb-2">
              <input
                type="text"
                value={avoidInput}
                onChange={(e) => setAvoidInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    addAvoidTerm();
                  }
                }}
                placeholder="Add constraint (e.g. alcohol, violence, logos)..."
                className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-sm text-slate-100"
              />
              <button
                type="button"
                onClick={addAvoidTerm}
                className="bg-slate-800 hover:bg-slate-700 text-slate-200 px-4 py-2 rounded-xl text-sm"
              >
                Add
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {avoidList.map((term) => (
                <span
                  key={term}
                  className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-slate-800 border border-slate-700 text-xs text-slate-300"
                >
                  <span>{term}</span>
                  <button type="button" onClick={() => removeAvoidTerm(term)} className="hover:text-rose-400">
                    &times;
                  </button>
                </span>
              ))}
            </div>
          </div>

          {/* Captions Options */}
          <div className="grid grid-cols-2 gap-4 pt-2 border-t border-slate-800">
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={burnCaptions}
                onChange={(e) => setBurnCaptions(e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600 focus:ring-0 bg-slate-950 border-slate-800"
              />
              <span className="text-sm text-slate-300">Burn subtitles into video</span>
            </label>
            <label className="flex items-center space-x-3 cursor-pointer">
              <input
                type="checkbox"
                checked={generateSrt}
                onChange={(e) => setGenerateSrt(e.target.checked)}
                className="w-4 h-4 rounded text-indigo-600 focus:ring-0 bg-slate-950 border-slate-800"
              />
              <span className="text-sm text-slate-300">Generate captions.srt</span>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end space-x-4">
          <button
            type="button"
            onClick={onCancel}
            className="px-5 py-2.5 rounded-xl text-sm font-medium text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800 text-white font-medium px-6 py-2.5 rounded-xl shadow-lg shadow-indigo-600/30 transition transform active:scale-95"
          >
            {submitting ? (
              <span>Submitting Job...</span>
            ) : (
              <>
                <span>Generate Video</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
};
