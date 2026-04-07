"use client";

import { useRouter } from "next/navigation";
import { Shield, LogOut } from "lucide-react";
import { authApi, clearTokens } from "@/lib/api";

interface TopbarProps {
  userEmail?: string;
  isLive?: boolean;
}

export function Topbar({ userEmail, isLive = false }: TopbarProps) {
  const router = useRouter();

  async function handleLogout() {
    try { await authApi.logout(); } catch { /* ignore */ }
    clearTokens();
    document.cookie = "auth_session=; path=/; max-age=0";
    router.replace("/login");
  }

  return (
    <header className="bg-white border-b border-gray-100 px-5 py-3 flex items-center justify-between">
      <div className="flex items-center gap-5">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-red-50 flex items-center justify-center">
            <Shield size={14} className="text-red-500" />
          </div>
          <span className="text-sm font-medium text-gray-900">SecureAI Monitor</span>
        </div>
        <nav className="flex gap-1">
          {["Dashboard", "Logs", "Detection", "Users", "Settings"].map((item) => (
            <button
              key={item}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                item === "Dashboard"
                  ? "bg-gray-100 text-gray-900 font-medium"
                  : "text-gray-500 hover:text-gray-900 hover:bg-gray-50"
              }`}
            >
              {item}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex items-center gap-4">
        {isLive && (
          <div className="flex items-center gap-1.5">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500" />
            </span>
            <span className="text-xs text-green-600">Live</span>
          </div>
        )}
        {userEmail && (
          <span className="text-xs text-gray-400">{userEmail}</span>
        )}
        <button
          onClick={handleLogout}
          className="flex items-center gap-1 text-xs text-gray-400 hover:text-gray-700 transition-colors"
        >
          <LogOut size={13} />
          Sign out
        </button>
      </div>
    </header>
  );
}
