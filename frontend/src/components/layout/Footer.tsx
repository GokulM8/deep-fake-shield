import { Link } from "@tanstack/react-router";
import { ShieldHalf } from "lucide-react";

export function Footer() {
  return (
    <footer className="print-hide mt-24 border-t border-border">
      <div className="mx-auto grid max-w-7xl gap-6 px-4 py-10 sm:px-6 md:grid-cols-[minmax(0,1fr)_auto] md:items-center">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5">
            <ShieldHalf className="h-4 w-4 shrink-0 text-primary" />
            <span className="font-display text-sm font-semibold tracking-[0.14em]">
              DEEPFAKE SHIELD
            </span>
          </div>
          <p className="mt-2 max-w-xl text-xs leading-relaxed text-muted-foreground">
            AI-assisted digital media authenticity and forensic analysis. Results are investigative
            signals, not legal certainty. This build runs on demonstration fixtures — no live model
            inference is performed.
          </p>
        </div>
        <nav className="flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
          <Link to="/analyze" className="transition-colors hover:text-foreground">
            Analyze
          </Link>
          <Link to="/investigations" className="transition-colors hover:text-foreground">
            Investigations
          </Link>
          <Link to="/about" className="transition-colors hover:text-foreground">
            About
          </Link>
        </nav>
      </div>
    </footer>
  );
}
