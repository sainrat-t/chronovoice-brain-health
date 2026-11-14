import { AudioLines } from "lucide-react";
import { Link, Outlet } from "react-router-dom";

export function Layout() {
  return (
    <div className="min-h-screen">
      <div className="no-print bg-slate-800 px-4 py-1.5 text-center text-xs font-medium tracking-wide text-slate-100">
        Demo workspace · synthetic data · screening support only, not a diagnosis
      </div>
      <header className="no-print border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          <Link to="/" className="flex items-center gap-2.5 text-slate-800">
            <span className="flex size-8 items-center justify-center rounded-lg bg-slate-800 text-sage-200">
              <AudioLines aria-hidden className="size-5" />
            </span>
            <span className="text-[15px] font-semibold tracking-tight">ChronoVoice Brain</span>
          </Link>
          <nav className="text-sm text-slate-600">
            <Link to="/" className="rounded-md px-2 py-1 hover:bg-slate-100 hover:text-slate-900">
              People
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  );
}
