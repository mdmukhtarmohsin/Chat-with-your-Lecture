"use client";

import { useState, useEffect, useCallback } from "react";
import { Video, ProcessingStatus } from "@/types/video";

interface VideoListProps {
  onVideoSelect: (video: Video) => void;
}

export function VideoList({ onVideoSelect }: VideoListProps) {
  const [videos, setVideos] = useState<Video[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchVideos = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const response = await fetch("http://localhost:8000/api/v1/videos/");

      if (!response.ok) {
        throw new Error(`Failed to fetch videos: ${response.statusText}`);
      }

      const data = await response.json();
      setVideos(data.videos || []);
    } catch (err) {
      console.error("Error fetching videos:", err);
      setError(err instanceof Error ? err.message : "Failed to load videos");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchVideos();
  }, [fetchVideos]);

  const getStatusBadge = (status: ProcessingStatus) => {
    const statusConfig = {
      [ProcessingStatus.UPLOADING]: {
        color: "bg-blue-100 text-blue-800",
        text: "Uploading",
      },
      [ProcessingStatus.PROCESSING]: {
        color: "bg-yellow-100 text-yellow-800",
        text: "Processing",
      },
      [ProcessingStatus.TRANSCRIBING]: {
        color: "bg-purple-100 text-purple-800",
        text: "Transcribing",
      },
      [ProcessingStatus.CHUNKING]: {
        color: "bg-indigo-100 text-indigo-800",
        text: "Chunking",
      },
      [ProcessingStatus.EMBEDDING]: {
        color: "bg-orange-100 text-orange-800",
        text: "Embedding",
      },
      [ProcessingStatus.COMPLETED]: {
        color: "bg-green-100 text-green-800",
        text: "Ready",
      },
      [ProcessingStatus.FAILED]: {
        color: "bg-red-100 text-red-800",
        text: "Failed",
      },
    };

    return statusConfig[status] || statusConfig[ProcessingStatus.PROCESSING];
  };

  const formatDuration = (seconds: number) => {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  };

  const formatDate = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
      });
    } catch {
      return "Unknown date";
    }
  };

  if (loading) {
    return (
      <div className="space-y-3">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="p-4 border border-gray-200 rounded-lg animate-pulse"
          >
            <div className="h-4 bg-gray-200 rounded w-3/4 mb-2"></div>
            <div className="h-3 bg-gray-200 rounded w-1/2 mb-2"></div>
            <div className="h-5 bg-gray-200 rounded w-16"></div>
          </div>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <div className="text-3xl mb-2">⚠️</div>
        <p className="text-red-600 mb-4">{error}</p>
        <button onClick={fetchVideos} className="btn-primary">
          Retry
        </button>
      </div>
    );
  }

  if (videos.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <div className="text-3xl mb-2">📭</div>
        <p>No videos uploaded yet</p>
        <p className="text-sm mt-1">
          Upload your first lecture video to get started
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {videos.map((video) => {
        const statusBadge = getStatusBadge(video.processing_status);
        const isClickable =
          video.processing_status === ProcessingStatus.COMPLETED;

        return (
          <div
            key={video.video_id}
            className={`p-4 border border-gray-200 rounded-lg transition-colors ${
              isClickable
                ? "cursor-pointer hover:bg-gray-50 hover:border-gray-300"
                : "cursor-not-allowed opacity-75"
            }`}
            onClick={() => isClickable && onVideoSelect(video)}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1 min-w-0">
                <h4 className="font-medium text-gray-900 truncate">
                  {video.title}
                </h4>
                <div className="text-sm text-gray-600 mt-1 space-y-1">
                  <p>
                    {formatDuration(video.duration)} • {video.total_chunks || 0}{" "}
                    chunks
                  </p>
                  <p>Uploaded {formatDate(video.upload_timestamp)}</p>
                </div>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between">
              <span
                className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${statusBadge.color}`}
              >
                {statusBadge.text}
              </span>

              {!isClickable &&
                video.processing_status !== ProcessingStatus.FAILED && (
                  <div className="flex items-center text-xs text-gray-500">
                    <div className="loading-dots mr-2">
                      <div></div>
                      <div></div>
                      <div></div>
                      <div></div>
                    </div>
                    Processing...
                  </div>
                )}

              {video.processing_status === ProcessingStatus.FAILED && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    // TODO: Implement retry processing
                    console.log("Retry processing for:", video.video_id);
                  }}
                  className="text-xs text-blue-600 hover:text-blue-800"
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        );
      })}

      <div className="pt-2">
        <button onClick={fetchVideos} className="btn-outline w-full">
          Refresh
        </button>
      </div>
    </div>
  );
}
