"use client";

import { useState, useRef, useEffect } from "react";
import { Video } from "@/types/video";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: Array<{
    text: string;
    start_time: number;
    end_time: number;
  }>;
}

interface ChatInterfaceProps {
  video: Video;
}

export function ChatInterface({ video }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage: ChatMessage = {
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `http://localhost:8000/api/v1/chat/${video.video_id}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            question: userMessage.content,
            conversation_history: messages.map((m) => ({
              role: m.role,
              content: m.content,
            })),
          }),
        }
      );

      if (!response.ok) {
        throw new Error(`Chat request failed: ${response.statusText}`);
      }

      const data = await response.json();

      const assistantMessage: ChatMessage = {
        role: "assistant",
        content:
          data.answer || "I apologize, but I couldn't generate a response.",
        timestamp: new Date(),
        sources: data.relevant_chunks || [],
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error("Chat error:", err);
      setError(err instanceof Error ? err.message : "Failed to send message");

      // Add error message to chat
      const errorMessage: ChatMessage = {
        role: "assistant",
        content:
          "I'm sorry, I'm having trouble connecting to the chat service. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp: Date) => {
    return timestamp.toLocaleTimeString("en-US", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatTime = (seconds: number) => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, "0")}`;
  };

  const handleTimeClick = (seconds: number) => {
    // TODO: Implement video seeking when video player is added
    console.log(`Jump to ${formatTime(seconds)}`);
  };

  const clearChat = () => {
    setMessages([]);
    setError(null);
  };

  return (
    <div className="h-full flex flex-col">
      {/* Chat Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-gray-900 truncate">
              Chat with "{video.title}"
            </h3>
            <p className="text-sm text-gray-600">
              Ask questions about the lecture content
            </p>
          </div>
          {messages.length > 0 && (
            <button
              onClick={clearChat}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Clear Chat
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center py-8 text-gray-500">
            <div className="text-4xl mb-4">💬</div>
            <h4 className="text-lg font-medium text-gray-900 mb-2">
              Start a conversation about this lecture
            </h4>
            <p className="text-sm">
              Ask about concepts, examples, or specific topics covered in the
              video
            </p>
            <div className="mt-4 space-y-2 text-sm text-gray-600">
              <p>Try asking:</p>
              <div className="space-y-1 text-left max-w-md mx-auto">
                <p>• "What are the main topics covered?"</p>
                <p>• "Explain the concept discussed around minute 15"</p>
                <p>• "What examples were given for [topic]?"</p>
                <p>• "Summarize the key points"</p>
              </div>
            </div>
          </div>
        )}

        {messages.map((message, index) => (
          <div
            key={index}
            className={`chat-message ${
              message.role === "user"
                ? "chat-message-user"
                : "chat-message-assistant"
            }`}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="font-medium">
                {message.role === "user" ? "You" : "AI Assistant"}
              </div>
              <div className="text-xs text-gray-500">
                {formatTimestamp(message.timestamp)}
              </div>
            </div>

            <div className="whitespace-pre-wrap">{message.content}</div>

            {message.sources && message.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-200">
                <div className="text-xs text-gray-600 mb-2">
                  Sources from the lecture:
                </div>
                <div className="space-y-2">
                  {message.sources.map((source, idx) => (
                    <div
                      key={idx}
                      className="text-xs bg-gray-50 p-2 rounded border-l-2 border-blue-200"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <button
                          onClick={() => handleTimeClick(source.start_time)}
                          className="text-blue-600 hover:text-blue-800 font-medium"
                        >
                          {formatTime(source.start_time)} -{" "}
                          {formatTime(source.end_time)}
                        </button>
                      </div>
                      <p className="text-gray-700 italic">
                        "{source.text.substring(0, 150)}..."
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="chat-message-assistant">
            <div className="flex items-center justify-between mb-2">
              <div className="font-medium">AI Assistant</div>
              <div className="text-xs text-gray-500">
                {formatTimestamp(new Date())}
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <div className="loading-dots">
                <div></div>
                <div></div>
                <div></div>
                <div></div>
              </div>
              <span className="text-sm text-gray-500">Thinking...</span>
            </div>
          </div>
        )}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex space-x-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask a question about the lecture..."
            className="input flex-1"
            disabled={loading}
            maxLength={500}
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || loading}
            className="btn-primary px-6"
          >
            {loading ? "..." : "Send"}
          </button>
        </div>
        <div className="text-xs text-gray-500 mt-1 text-right">
          {input.length}/500
        </div>
      </div>
    </div>
  );
}
