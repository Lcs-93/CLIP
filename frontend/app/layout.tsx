import "./globals.css";
import type { Metadata } from "next";
import { Space_Grotesk } from "next/font/google";

import { AppShell } from "@/components/app/app-shell";
import { ThemeProvider } from "@/components/theme-provider";
import { ToastProvider } from "@/components/ui/toast";

const spaceGrotesk = Space_Grotesk({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Clip Video SaaS",
  description: "Local AI clip workflow studio",
};

const themeInitScript = `
(() => {
  try {
    const stored = localStorage.getItem("theme");
    const resolved = stored === "dark" ? "dark" : "light";
    document.documentElement.classList.toggle("dark", resolved === "dark");
    document.documentElement.dataset.theme = resolved;
  } catch (error) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className={spaceGrotesk.className}>
        <ThemeProvider>
          <ToastProvider>
            <AppShell>{children}</AppShell>
          </ToastProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
