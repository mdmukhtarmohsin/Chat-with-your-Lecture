import "./globals.css";
import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Toaster } from "react-hot-toast";
import { QueryClient, QueryClientProvider } from "react-query";
import { ReactQueryProvider } from "@/components/providers/ReactQueryProvider";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Chat with your Lecture - Video RAG",
  description: "Process lecture videos and chat with the content using AI",
  keywords: [
    "lecture",
    "video",
    "AI",
    "RAG",
    "chat",
    "education",
    "transcript",
  ],
  authors: [{ name: "Lecture RAG Team" }],
  viewport: "width=device-width, initial-scale=1",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="h-full">
      <body className={`${inter.className} h-full bg-gray-50 antialiased`}>
        <ReactQueryProvider>
          <div className="min-h-screen flex flex-col">
            <header className="bg-white shadow-sm border-b border-gray-200">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="flex justify-between items-center h-16">
                  <div className="flex items-center">
                    <h1 className="text-xl font-semibold text-gray-900">
                      📚 Chat with your Lecture
                    </h1>
                  </div>
                  <div className="text-sm text-gray-500">
                    AI-powered lecture analysis
                  </div>
                </div>
              </div>
            </header>

            <main className="flex-1 overflow-hidden">{children}</main>

            <footer className="bg-white border-t border-gray-200 py-4">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="text-center text-sm text-gray-500">
                  <p>
                    Built with Next.js, FastAPI, and Gemini AI •
                    <span className="ml-1">
                      Process videos, chat with content
                    </span>
                  </p>
                </div>
              </div>
            </footer>
          </div>

          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: "#fff",
                color: "#374151",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                fontSize: "14px",
              },
              success: {
                iconTheme: {
                  primary: "#10b981",
                  secondary: "#fff",
                },
              },
              error: {
                iconTheme: {
                  primary: "#ef4444",
                  secondary: "#fff",
                },
              },
            }}
          />
        </ReactQueryProvider>
      </body>
    </html>
  );
}
