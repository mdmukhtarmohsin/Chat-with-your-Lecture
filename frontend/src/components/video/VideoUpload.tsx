"use client";

import { useState, useRef, useCallback } from "react";

interface VideoUploadProps {
  onUploadSuccess: () => void;
}

export function VideoUpload({ onUploadSuccess }: VideoUploadProps) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    async (files: FileList) => {
      const file = files[0];
      if (!file) return;

      // Validate file type
      if (!file.type.startsWith("video/")) {
        setError("Please select a video file");
        return;
      }

      // Validate file size (max 2GB)
      const maxSize = 2 * 1024 * 1024 * 1024; // 2GB
      if (file.size > maxSize) {
        setError("File size must be less than 2GB");
        return;
      }

      setError(null);
      setUploading(true);
      setProgress(0);

      try {
        const formData = new FormData();
        formData.append("file", file);

        const response = await fetch(
          "http://localhost:8000/api/v1/videos/upload",
          {
            method: "POST",
            body: formData,
          }
        );

        if (!response.ok) {
          throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        console.log("Upload successful:", result);

        setProgress(100);
        setTimeout(() => {
          setUploading(false);
          setProgress(0);
          onUploadSuccess();
        }, 1000);
      } catch (err) {
        console.error("Upload error:", err);
        setError(err instanceof Error ? err.message : "Upload failed");
        setUploading(false);
        setProgress(0);
      }
    },
    [onUploadSuccess]
  );

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setDragActive(false);

      if (e.dataTransfer.files && e.dataTransfer.files[0]) {
        handleFiles(e.dataTransfer.files);
      }
    },
    [handleFiles]
  );

  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files[0]) {
        handleFiles(e.target.files);
      }
    },
    [handleFiles]
  );

  return (
    <div className="space-y-4">
      <div
        className={`p-8 border-2 border-dashed rounded-lg text-center transition-colors cursor-pointer ${
          dragActive
            ? "border-blue-400 bg-blue-50"
            : uploading
            ? "border-gray-300 bg-gray-50 cursor-not-allowed"
            : "border-gray-300 hover:border-gray-400"
        }`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={!uploading ? handleFileSelect : undefined}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleInputChange}
          className="hidden"
          disabled={uploading}
        />

        <div className="text-6xl mb-4">{uploading ? "⏳" : "📹"}</div>

        <h3 className="text-lg font-medium text-gray-900 mb-2">
          {uploading ? "Uploading Video..." : "Upload Lecture Video"}
        </h3>

        <p className="text-sm text-gray-600 mb-4">
          {uploading
            ? `Processing your video (${progress}%)`
            : "Drag and drop a video file here, or click to select"}
        </p>

        {!uploading && (
          <button className="btn-primary">Choose Video File</button>
        )}

        {uploading && (
          <div className="w-full bg-gray-200 rounded-full h-2 mt-4">
            <div
              className="bg-blue-600 h-2 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        )}
      </div>

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}

      <div className="text-xs text-gray-500 space-y-1">
        <p>• Supported formats: MP4, MOV, AVI, MKV</p>
        <p>• Maximum file size: 2GB</p>
        <p>• Processing may take 5-15 minutes depending on video length</p>
      </div>
    </div>
  );
}
