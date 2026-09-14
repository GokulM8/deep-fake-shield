import { Link, useRouterState } from "@tanstack/react-router";
import {
  FolderSearch,
  Info,
  Menu,
  Moon,
  Pencil,
  ShieldHalf,
  Sun,
  UserRound,
  X,
} from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

const NAV = [
  { to: "/analyze", label: "Analyze" },
  { to: "/investigations", label: "Investigations" },
  { to: "/about", label: "About" },
] as const;

function ThemeToggle() {
  const [light, setLight] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle("light", light);
  }, [light]);

  return (
    <button
      type="button"
      aria-label="Toggle theme"
      onClick={() => setLight((v) => !v)}
      className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
    >
      {light ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
    </button>
  );
}

type AnalystProfile = {
  name: string;
  role: string;
  org: string;
  caseLoad: number;
};

const DEFAULT_ANALYST: AnalystProfile = {
  name: "A. Vetrov",
  role: "Forensic Analyst",
  org: "DeepFake Shield Lab",
  caseLoad: 3,
};

const PROFILE_KEY = "dfs.analyst-profile";

function ProfileMenu() {
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [profile, setProfile] = useState<AnalystProfile>(DEFAULT_ANALYST);
  const [draft, setDraft] = useState<AnalystProfile>(DEFAULT_ANALYST);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      if (!raw) return;
      const saved = JSON.parse(raw) as Partial<AnalystProfile>;
      const merged = { ...DEFAULT_ANALYST, ...saved };
      setProfile(merged);
      setDraft(merged);
    } catch {
      /* ignore malformed saved profile */
    }
  }, []);

  useEffect(() => {
    setOpen(false);
    setEditing(false);
  }, [pathname]);

  const startEdit = () => {
    setDraft(profile);
    setEditing(true);
  };

  const save = (e: React.FormEvent) => {
    e.preventDefault();
    const next: AnalystProfile = {
      name: draft.name.trim() || DEFAULT_ANALYST.name,
      role: draft.role.trim() || DEFAULT_ANALYST.role,
      org: draft.org.trim() || DEFAULT_ANALYST.org,
      caseLoad: Number.isFinite(draft.caseLoad) ? Math.max(0, Math.round(draft.caseLoad)) : 0,
    };
    setProfile(next);
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(next));
    } catch {
      /* storage unavailable */
    }
    setEditing(false);
  };

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <div className="relative hidden sm:block">
      <button
        type="button"
        aria-label="Profile"
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={cn(
          "grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground",
          open && "border-border-strong text-foreground bg-secondary/60",
        )}
      >
        <UserRound className="h-4 w-4" />
      </button>

      {open ? (
        <>
          <div className="fixed inset-0 z-40" aria-hidden onClick={() => setOpen(false)} />
          <div
            role="menu"
            className="absolute right-0 z-50 mt-2 w-72 rounded-md border border-border bg-card p-3 shadow-panel"
          >
            <div className="flex items-center gap-3 border-b border-border pb-3">
              <span className="grid h-10 w-10 shrink-0 place-items-center rounded-md border border-primary/30 bg-primary/10">
                <UserRound className="h-5 w-5 text-primary" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-foreground">{profile.name}</p>
                <p className="truncate text-xs text-muted-foreground">
                  {profile.role} · {profile.org}
                </p>
              </div>
              {!editing ? (
                <button
                  type="button"
                  onClick={startEdit}
                  aria-label="Edit profile"
                  className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-border text-muted-foreground transition-colors hover:border-border-strong hover:text-foreground"
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
              ) : null}
            </div>

            {editing ? (
              <form onSubmit={save} className="flex flex-col gap-2 py-3">
                <label className="flex flex-col gap-1">
                  <span className="label-caps text-[10px] text-muted-foreground">Name</span>
                  <input
                    value={draft.name}
                    autoFocus
                    onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
                    className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground outline-none focus:border-primary/60"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="label-caps text-[10px] text-muted-foreground">Role</span>
                  <input
                    value={draft.role}
                    onChange={(e) => setDraft((d) => ({ ...d, role: e.target.value }))}
                    className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground outline-none focus:border-primary/60"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="label-caps text-[10px] text-muted-foreground">Organisation</span>
                  <input
                    value={draft.org}
                    onChange={(e) => setDraft((d) => ({ ...d, org: e.target.value }))}
                    className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground outline-none focus:border-primary/60"
                  />
                </label>
                <label className="flex flex-col gap-1">
                  <span className="label-caps text-[10px] text-muted-foreground">Active cases</span>
                  <input
                    type="number"
                    min={0}
                    value={String(draft.caseLoad)}
                    onChange={(e) =>
                      setDraft((d) => ({
                        ...d,
                        caseLoad: Number(e.target.value),
                      }))
                    }
                    className="rounded-md border border-border bg-background px-2.5 py-1.5 text-sm text-foreground outline-none focus:border-primary/60"
                  />
                </label>
                <div className="mt-1 flex items-center gap-2">
                  <button
                    type="submit"
                    className="flex-1 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90"
                  >
                    Save
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditing(false)}
                    className="rounded-md border border-border px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                  >
                    Cancel
                  </button>
                </div>
              </form>
            ) : (
              <div className="flex flex-col gap-1 py-2">
                <Link
                  to="/investigations"
                  role="menuitem"
                  className="flex items-center justify-between rounded-md px-2.5 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                >
                  <span className="flex items-center gap-2">
                    <FolderSearch className="h-4 w-4" />
                    My investigations
                  </span>
                  <span className="label-caps text-[10px] text-primary">{profile.caseLoad}</span>
                </Link>
                <Link
                  to="/analyze"
                  role="menuitem"
                  className="flex items-center gap-2 rounded-md px-2.5 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                >
                  <ShieldHalf className="h-4 w-4" />
                  New analysis
                </Link>
                <Link
                  to="/about"
                  role="menuitem"
                  className="flex items-center gap-2 rounded-md px-2.5 py-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
                >
                  <Info className="h-4 w-4" />
                  Methodology & limits
                </Link>
              </div>
            )}

            <p className="border-t border-border pt-2 text-[11px] leading-relaxed text-muted-foreground">
              Demo analyst profile, saved in this browser only. Accounts and sign-in are not part of
              this build.
            </p>
          </div>
        </>
      ) : null}
    </div>
  );
}

export function Navbar() {
  const [open, setOpen] = useState(false);
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(() => {
    setOpen(false);
  }, [pathname]);

  return (
    <header className="print-hide sticky top-0 z-50 border-b border-border bg-background/85 backdrop-blur-xl">
      <div className="mx-auto grid max-w-7xl grid-cols-[minmax(0,1fr)_auto] items-center gap-4 px-4 py-3 sm:px-6">
        <div className="flex min-w-0 items-center gap-8">
          <Link to="/" className="flex min-w-0 items-center gap-2.5">
            <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-primary/30 bg-primary/10">
              <ShieldHalf className="h-4 w-4 text-primary" />
            </span>
            <span className="truncate font-display text-sm font-semibold tracking-[0.14em]">
              DEEPFAKE SHIELD
            </span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className="rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground"
                activeProps={{ className: "text-foreground bg-secondary/60" }}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          <span className="hidden items-center gap-2 rounded-md border border-border px-2.5 py-1.5 lg:inline-flex">
            <span className="relative grid h-2 w-2 place-items-center">
              <span className="absolute h-2 w-2 animate-pulse-ring rounded-full bg-primary" />
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
            </span>
            <span className="label-caps">System Status: Online</span>
          </span>

          <div className="hidden sm:block">
            <ThemeToggle />
          </div>

          <ProfileMenu />

          <Link
            to="/analyze"
            className="hidden rounded-md bg-primary px-3.5 py-2 text-sm font-medium text-primary-foreground transition-opacity hover:opacity-90 sm:inline-flex"
          >
            Analyze Media
          </Link>

          <button
            type="button"
            aria-label="Menu"
            onClick={() => setOpen((v) => !v)}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-md border border-border md:hidden"
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      <div
        className={cn(
          "overflow-hidden border-t border-border transition-[max-height] duration-300 md:hidden",
          open ? "max-h-80" : "max-h-0 border-t-0",
        )}
      >
        <nav className="flex flex-col gap-1 px-4 py-3">
          {NAV.map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className="rounded-md px-3 py-2.5 text-sm text-muted-foreground"
              activeProps={{ className: "text-foreground bg-secondary/60" }}
            >
              {item.label}
            </Link>
          ))}
          <div className="mt-2 flex items-center gap-2">
            <ThemeToggle />
            <Link
              to="/analyze"
              className="flex-1 rounded-md bg-primary px-3.5 py-2.5 text-center text-sm font-medium text-primary-foreground"
            >
              Analyze Media
            </Link>
          </div>
        </nav>
      </div>
    </header>
  );
}
