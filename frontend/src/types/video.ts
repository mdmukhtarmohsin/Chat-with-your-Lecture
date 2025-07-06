export interface Video {
  video_id: string;
  title: string;
  duration: number;
  total_chunks: number;
  processing_status: ProcessingStatus;
  upload_timestamp: string;
}

export interface VideoMetadata {
  id: string;
  filename: string;
  title?: string;
  duration: number;
  file_size: number;
  upload_timestamp: string;
  processing_status: ProcessingStatus;
  audio_path?: string;
  transcript_path?: string;
  total_chunks?: number;
  processing_error?: string;
}

export interface TranscriptChunk {
  id: string;
  video_id: string;
  text: string;
  start_time: number;
  end_time: number;
  chunk_index: number;
  word_count: number;
}

export enum ProcessingStatus {
  UPLOADING = "uploading",
  PROCESSING = "processing",
  TRANSCRIBING = "transcribing",
  CHUNKING = "chunking",
  EMBEDDING = "embedding",
  COMPLETED = "completed",
  FAILED = "failed",
}

export interface VideoProcessingResponse {
  video_id: string;
  status: ProcessingStatus;
  message: string;
  progress?: number;
}

export interface VideoListResponse {
  videos: Video[];
  total: number;
}

export interface VideoDetailResponse {
  metadata: VideoMetadata;
  chunks: TranscriptChunk[];
}
