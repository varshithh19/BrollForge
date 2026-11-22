export interface CaptionsConfig {
  burn_in: boolean;
  srt: boolean;
}

export interface SceneInput {
  text: string;
  visual_hint?: string;
}

export interface CreateJobPayload {
  audio_url?: string;
  script?: string;
  scenes?: SceneInput[];
  voice?: string;
  aspect_ratios: string[];
  style: string;
  avoid: string[];
  captions: CaptionsConfig;
  callback_url?: string;
}

export interface VideoResult {
  url: string;
  width: number;
  height: number;
  duration: number;
  file_size: number;
  aspect_ratio: string;
}

export interface ResultLinks {
  videos?: Record<string, VideoResult>;
  timeline?: string;
  manifest?: string;
  captions_srt?: string;
}

export interface JobError {
  code: string;
  message: string;
  retryable: boolean;
  details?: Record<string, any>;
}

export interface Job {
  job_id: string;
  status: 'queued' | 'running' | 'succeeded' | 'failed';
  progress: number;
  stage: string;
  input_type?: string;
  aspect_ratios?: string[];
  created_at: string;
  updated_at: string;
  result_links?: ResultLinks;
  warnings?: string[];
  error?: JobError;
}

export interface TimelineScene {
  scene_id: string;
  scene_index: number;
  text: string;
  start_time: number;
  end_time: number;
  duration: number;
  visual_hint?: string;
  semantic_description?: string;
  search_query: string;
  selected_clip?: string;
  provider?: string;
  provider_asset_id?: string;
  source_url?: string;
  licence_name?: string;
  licence_url?: string;
  attribution?: string;
  creator?: string;
  is_ai_generated: boolean;
  relevance_score: number;
  score_method: string;
  selection_reason?: string;
  aspect_ratio_outputs?: Record<string, string>;
  warnings?: string[];
}

export interface TimelineData {
  job_id: string;
  total_duration: number;
  scene_count: number;
  aspect_ratios: string[];
  scenes: TimelineScene[];
}
