import { useMemo, useId } from "react";
import { Edit3, X } from "lucide-react";

import {
  DurationFilterRule,
  FilterRule,
  NUMERIC_OPERATOR_OPTIONS,
  QUICK_PRESET_OPTIONS,
  ScoreFilterRule,
  StatusFilterRule,
  STATUS_OPERATOR_OPTIONS,
  TagFilterRule,
  TAG_OPERATOR_OPTIONS,
  formatRuleLabel,
} from "@/components/clips/filter-rules";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/cn";

interface FilterTokenProps {
  rule: FilterRule;
  open: boolean;
  availableStatuses: string[];
  availableTags: string[];
  onOpenChange: (open: boolean) => void;
  onChange: (nextRule: FilterRule) => void;
  onRemove: () => void;
}

const editorSelectClassName =
  "h-9 w-full rounded-lg border border-input bg-background/80 px-2.5 text-sm text-foreground outline-none transition focus-visible:ring-2 focus-visible:ring-ring";

function statusValueLabel(value: string) {
  if (value === "ready") return "Ready";
  if (value === "not-ready") return "Not ready";
  return value.replace(/[-_]/g, " ");
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function RuleEditor({
  rule,
  availableStatuses,
  availableTags,
  onChange,
}: {
  rule: FilterRule;
  availableStatuses: string[];
  availableTags: string[];
  onChange: (nextRule: FilterRule) => void;
}) {
  const tagsListId = useId();

  const statusOptions = useMemo(() => {
    const unique = new Set<string>(["ready", "not-ready"]);
    availableStatuses.forEach((status) => {
      const normalized = status.trim().toLowerCase();
      if (normalized) unique.add(normalized);
    });
    return Array.from(unique);
  }, [availableStatuses]);

  if (rule.type === "score") {
    return (
      <div className="space-y-2.5">
        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Operator
          <select
            value={rule.operator}
            onChange={(event) => onChange({ ...rule, operator: event.target.value as ScoreFilterRule["operator"] })}
            className={editorSelectClassName}
          >
            {NUMERIC_OPERATOR_OPTIONS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Value (%)
          <Input
            type="number"
            min={0}
            max={100}
            value={rule.value}
            onChange={(event) => {
              const parsed = Number(event.target.value);
              if (!Number.isFinite(parsed)) {
                onChange({ ...rule, value: 0 });
                return;
              }
              onChange({ ...rule, value: Math.round(clampNumber(parsed, 0, 100)) });
            }}
            className="h-9"
          />
        </label>
      </div>
    );
  }

  if (rule.type === "duration") {
    return (
      <div className="space-y-2.5">
        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Operator
          <select
            value={rule.operator}
            onChange={(event) => onChange({ ...rule, operator: event.target.value as DurationFilterRule["operator"] })}
            className={editorSelectClassName}
          >
            {NUMERIC_OPERATOR_OPTIONS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Value (s)
          <Input
            type="number"
            min={0}
            max={7200}
            value={rule.value}
            onChange={(event) => {
              const parsed = Number(event.target.value);
              if (!Number.isFinite(parsed)) {
                onChange({ ...rule, value: 0 });
                return;
              }
              onChange({ ...rule, value: Math.round(clampNumber(parsed, 0, 7200)) });
            }}
            className="h-9"
          />
        </label>
      </div>
    );
  }

  if (rule.type === "status") {
    return (
      <div className="space-y-2.5">
        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Operator
          <select
            value={rule.operator}
            onChange={(event) =>
              onChange({
                ...rule,
                operator: event.target.value as StatusFilterRule["operator"],
              })
            }
            className={editorSelectClassName}
          >
            {STATUS_OPERATOR_OPTIONS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Status
          <select
            value={rule.value}
            onChange={(event) => onChange({ ...rule, value: event.target.value })}
            className={editorSelectClassName}
          >
            {statusOptions.map((status) => (
              <option key={status} value={status}>
                {statusValueLabel(status)}
              </option>
            ))}
          </select>
        </label>
      </div>
    );
  }

  return (
    <div className="space-y-2.5">
      <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        Mode
        <select
          value={rule.operator}
          onChange={(event) => {
            const nextOperator = event.target.value as TagFilterRule["operator"];
            if (nextOperator === "quick") {
              onChange({ ...rule, operator: nextOperator, value: "best" });
              return;
            }

            const nextValue =
              rule.operator === "quick"
                ? availableTags[0] ?? ""
                : rule.value;

            onChange({ ...rule, operator: nextOperator, value: nextValue });
          }}
          className={editorSelectClassName}
        >
          {TAG_OPERATOR_OPTIONS.map((item) => (
            <option key={item.value} value={item.value}>
              {item.label}
            </option>
          ))}
        </select>
      </label>

      {rule.operator === "quick" ? (
        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Preset
          <select
            value={rule.value}
            onChange={(event) => onChange({ ...rule, value: event.target.value })}
            className={editorSelectClassName}
          >
            {QUICK_PRESET_OPTIONS.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.12em] text-muted-foreground">
          Tag
          <Input
            value={rule.value}
            list={availableTags.length ? tagsListId : undefined}
            onChange={(event) => onChange({ ...rule, value: event.target.value })}
            placeholder="e.g. hook, gaming..."
            className="h-9"
          />
          {availableTags.length ? (
            <datalist id={tagsListId}>
              {availableTags.map((tag) => (
                <option key={tag} value={tag} />
              ))}
            </datalist>
          ) : null}
        </label>
      )}
    </div>
  );
}

export function FilterToken({
  rule,
  open,
  availableStatuses,
  availableTags,
  onOpenChange,
  onChange,
  onRemove,
}: FilterTokenProps) {
  const label = formatRuleLabel(rule);

  return (
    <div className="relative inline-flex shrink-0 items-center">
      <button
        type="button"
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
        className={cn(
          "inline-flex h-9 items-center gap-1.5 rounded-full border border-primary/35 bg-primary/12 px-3 text-[11px] font-semibold uppercase tracking-[0.11em] text-primary transition hover:bg-primary/18",
          open && "ring-2 ring-primary/25"
        )}
      >
        <Edit3 className="h-3.5 w-3.5" />
        <span className="max-w-[220px] truncate">{label}</span>
      </button>

      <button
        type="button"
        aria-label={`Remove ${label}`}
        onClick={onRemove}
        className="ml-1 inline-flex h-7 w-7 items-center justify-center rounded-full border border-border/70 bg-background/70 text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
      >
        <X className="h-3.5 w-3.5" />
      </button>

      {open ? (
        <>
          <button
            type="button"
            aria-label="Close filter editor"
            className="fixed inset-0 z-40 cursor-default"
            onClick={() => onOpenChange(false)}
          />

          <div className="absolute left-0 top-[calc(100%+0.5rem)] z-50 w-[min(94vw,290px)] rounded-xl border border-border/75 bg-card/95 p-3 shadow-[0_22px_64px_-40px_rgba(15,23,42,0.62)] backdrop-blur-xl">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Edit filter
            </p>
            <RuleEditor
              rule={rule}
              availableStatuses={availableStatuses}
              availableTags={availableTags}
              onChange={onChange}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}
