"use client";

import { useState } from "react";
import { VideoUpload } from "@/components/video/VideoUpload";
import { VideoList } from "@/components/video/VideoList";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { Video } from "@/types/video";

export default function HomePage() {
  const [selectedVideo, setSelectedVideo] = useState<Video | null>(null);
  const [activeTab, setActiveTab] = useState<"upload" | "videos" | "chat">(
    "upload"
  );

  const handleVideoSelect = (video: Video) => {
    setSelectedVideo(video);
    setActiveTab("chat");
  };

  const handleVideoUploaded = () => {
    // Refresh video list and switch to videos tab
    setActiveTab("videos");
  };

  return (
    <div className="h-full flex">
      {/* Sidebar */}
      <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
        {/* Navigation Tabs */}
        <div className="border-b border-gray-200 p-4">
          <nav className="flex space-x-1">
            <button
              onClick={() => setActiveTab("upload")}
              className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === "upload"
                  ? "bg-primary-100 text-primary-700"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              }`}
            >
              Upload
            </button>
            <button
              onClick={() => setActiveTab("videos")}
              className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === "videos"
                  ? "bg-primary-100 text-primary-700"
                  : "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
              }`}
            >
              Videos
            </button>
            <button
              onClick={() => setActiveTab("chat")}
              disabled={!selectedVideo}
              className={`px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                activeTab === "chat" && selectedVideo
                  ? "bg-primary-100 text-primary-700"
                  : selectedVideo
                  ? "text-gray-500 hover:text-gray-700 hover:bg-gray-100"
                  : "text-gray-400 cursor-not-allowed"
              }`}
            >
              Chat
            </button>
          </nav>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-hidden">
          {activeTab === "upload" && (
            <div className="p-4 h-full">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Upload Video
              </h2>
              <VideoUpload onUploadSuccess={handleVideoUploaded} />
            </div>
          )}

          {activeTab === "videos" && (
            <div className="p-4 h-full">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Your Videos
              </h2>
              <VideoList onVideoSelect={handleVideoSelect} />
            </div>
          )}

          {activeTab === "chat" && selectedVideo && (
            <div className="p-4 h-full flex flex-col">
              <div className="mb-4">
                <h2 className="text-lg font-semibold text-gray-900">
                  Chat with Video
                </h2>
                <p className="text-sm text-gray-600 mt-1 truncate">
                  {selectedVideo.title}
                </p>
              </div>
              <div className="text-xs text-gray-500 mb-2">
                Duration: {Math.floor(selectedVideo.duration / 60)}:
                {(selectedVideo.duration % 60).toFixed(0).padStart(2, "0")}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col">
        {selectedVideo && activeTab === "chat" ? (
          <ChatInterface video={selectedVideo} />
        ) : (
          <div className="flex-1 flex items-center justify-center bg-gray-50">
            <div className="text-center max-w-md">
              {activeTab === "upload" ? (
                <>
                  <div className="text-6xl mb-4">📹</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Upload Your Lecture Video
                  </h3>
                  <p className="text-gray-600">
                    Upload a lecture video to get started. The AI will
                    transcribe it and create an intelligent chat interface for
                    you to ask questions about the content.
                  </p>
                </>
              ) : activeTab === "videos" ? (
                <>
                  <div className="text-6xl mb-4">📚</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Your Video Library
                  </h3>
                  <p className="text-gray-600">
                    Browse your uploaded videos and select one to start chatting
                    with its content. Processing may take a few minutes for new
                    uploads.
                  </p>
                </>
              ) : (
                <>
                  <div className="text-6xl mb-4">💬</div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    Select a Video to Chat
                  </h3>
                  <p className="text-gray-600">
                    Choose a processed video from your library to start asking
                    questions about the lecture content.
                  </p>
                </>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
