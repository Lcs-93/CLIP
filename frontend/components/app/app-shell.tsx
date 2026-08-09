"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { Cog } from "lucide-react";
import { motion } from "framer-motion";

import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";
import { getStoredActiveVideoId, useAppStore } from "@/store/app-store";

interface NavItem {
  label: string;
  href: string;
  isActive: boolean;
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isUploadPage = pathname === "/";

  const activeVideoId = useAppStore((state) => state.activeVideoId);
  const setActiveVideoId = useAppStore((state) => state.setActiveVideoId);
  const refreshVideos = useAppStore((state) => state.refreshVideos);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const queryVideoId = params.get("videoId");
    if (queryVideoId) {
      setActiveVideoId(queryVideoId);
    }
  }, [pathname, setActiveVideoId]);

  useEffect(() => {
    const storedVideoId = getStoredActiveVideoId();
    if (storedVideoId && !activeVideoId) {
      setActiveVideoId(storedVideoId);
    }
  }, [activeVideoId, setActiveVideoId]);

  useEffect(() => {
    refreshVideos().catch(() => null);
  }, [refreshVideos]);

  const clipsHref = activeVideoId ? `/clips?videoId=${activeVideoId}` : "/clips";
  const exportsHref = activeVideoId ? `/exports?videoId=${activeVideoId}` : "/exports";

  const navItems: NavItem[] = [
    { label: "Upload", href: "/", isActive: pathname === "/" },
    { label: "Clips", href: clipsHref, isActive: pathname === "/clips" || pathname.startsWith("/clips/") },
    { label: "Exports", href: exportsHref, isActive: pathname === "/exports" },
    { label: "Settings", href: "/settings", isActive: pathname === "/settings" },
  ];

  return (
    <div className="app-root [--app-header-offset:5.8rem] md:[--app-header-offset:4.55rem]">
      <div className="app-fused-backdrop pointer-events-none fixed inset-0 -z-20">
        <div className="app-fused-veil absolute inset-0" />
        <span className="wow-aurora-ribbon wow-aurora-ribbon-a" />
        <span className="wow-aurora-ribbon wow-aurora-ribbon-b" />
        <span className="wow-aurora-ribbon wow-aurora-ribbon-c" />
        <div className="wow-noise-overlay absolute inset-0 opacity-[0.11]" />
      </div>
      <motion.header
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.42, ease: [0.16, 1, 0.3, 1] }}
        className={cn("prime-header sticky top-0 z-50", isUploadPage && "prime-header-home")}
      >
        <div className="prime-header-line" />
        <div className="mx-auto w-full max-w-[1280px] px-4 sm:px-6 lg:px-10">
          <div className="hidden min-h-[4.15rem] items-center gap-4 md:grid md:grid-cols-[1fr_auto_1fr]">
            <Link href="/" className="prime-brand">
              <span className="prime-brand-badge">CS</span>
              <span className="prime-brand-text">Clip Shine</span>
            </Link>

            <nav className="prime-nav">
              {navItems.map((item) => (
                <Link key={item.label} href={item.href} className={cn("prime-nav-link group", item.isActive && "prime-nav-link-active")}>
                  <span className="relative z-10">{item.label}</span>
                  <span className="prime-nav-hover-line" />
                  {item.isActive ? (
                    <motion.span
                      layoutId="prime-nav-active-line"
                      className="prime-nav-active-line"
                      transition={{ type: "spring", stiffness: 480, damping: 40, mass: 0.62 }}
                    />
                  ) : null}
                </Link>
              ))}
            </nav>

            <div className="prime-actions justify-self-end">
              {activeVideoId && (
                <motion.span
                  initial={{ opacity: 0, y: -4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
                  className="prime-video-chip hidden lg:inline-flex"
                >
                  video {activeVideoId.slice(0, 8)}
                </motion.span>
              )}
              <ThemeToggle className="prime-action-btn" />
              <Button
                asChild
                variant="ghost"
                size="icon"
                className="prime-action-btn"
              >
                <Link href="/settings" aria-label="Settings">
                  <Cog className="h-4 w-4" />
                </Link>
              </Button>
            </div>
          </div>

          <div className="space-y-2.5 py-2.5 md:hidden">
            <div className="flex items-center justify-between gap-2">
              <Link href="/" className="prime-brand">
                <span className="prime-brand-badge">CS</span>
                <span className="prime-brand-text">Clip Shine</span>
              </Link>

              <div className="prime-actions">
                <ThemeToggle className="prime-action-btn" />
                <Button asChild variant="ghost" size="icon" className="prime-action-btn">
                  <Link href="/settings" aria-label="Settings">
                    <Cog className="h-4 w-4" />
                  </Link>
                </Button>
              </div>
            </div>

            <nav className={cn("prime-mobile-nav scrollbar-thin", isUploadPage && "prime-mobile-nav-home")}>
              {navItems.map((item) => (
                <Link
                  key={`mobile-${item.label}`}
                  href={item.href}
                  className={cn("prime-mobile-nav-link", item.isActive && "prime-mobile-nav-link-active")}
                >
                  <span className="relative z-10">{item.label}</span>
                  {item.isActive ? (
                    <motion.span
                      layoutId="prime-mobile-active-line"
                      className="prime-mobile-active-line"
                      transition={{ type: "spring", stiffness: 500, damping: 38, mass: 0.65 }}
                    />
                  ) : null}
                </Link>
              ))}
            </nav>
          </div>
        </div>
      </motion.header>

      <div className="app-main">{children}</div>
    </div>
  );
}
