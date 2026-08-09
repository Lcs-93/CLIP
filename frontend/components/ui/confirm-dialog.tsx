"use client";

import * as React from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Loader2, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/cn";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  confirmLabel?: string;
  cancelLabel?: string;
  confirmVariant?: "default" | "destructive";
  isConfirming?: boolean;
  onConfirm: () => void | Promise<void>;
  children?: React.ReactNode;
}

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  confirmVariant = "destructive",
  isConfirming = false,
  onConfirm,
  children,
}: ConfirmDialogProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay
          className={cn(
            "fixed inset-0 z-[100] bg-black/55 backdrop-blur-[2px]",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0"
          )}
        />
        <Dialog.Content
          className={cn(
            "fixed left-1/2 top-1/2 z-[110] w-[min(92vw,520px)] -translate-x-1/2 -translate-y-1/2 rounded-2xl border border-border/75 bg-card/95 p-5 shadow-[0_40px_100px_-48px_rgba(15,23,42,0.8)] backdrop-blur-xl sm:p-6",
            "data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95 data-[state=open]:slide-in-from-bottom-2",
            "data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[state=closed]:slide-out-to-bottom-2"
          )}
        >
          <div className="space-y-1">
            <Dialog.Title className="text-lg font-semibold text-foreground">{title}</Dialog.Title>
            {description ? (
              <Dialog.Description className="text-sm text-muted-foreground">{description}</Dialog.Description>
            ) : null}
          </div>

          {children ? <div className="mt-4">{children}</div> : null}

          <div className="mt-5 flex justify-end gap-2.5">
            <Dialog.Close asChild disabled={isConfirming}>
              <Button type="button" variant="outline" className="rounded-lg" disabled={isConfirming}>
                {cancelLabel}
              </Button>
            </Dialog.Close>
            <Button
              type="button"
              variant={confirmVariant === "destructive" ? "destructive" : "default"}
              className="rounded-lg"
              onClick={() => void onConfirm()}
              disabled={isConfirming}
            >
              {isConfirming ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              {isConfirming ? "Please wait..." : confirmLabel}
            </Button>
          </div>

          <Dialog.Close
            className="absolute right-3 top-3 rounded-md p-1 text-muted-foreground transition hover:bg-muted hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            aria-label="Close"
            disabled={isConfirming}
          >
            <X className="h-4 w-4" />
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

