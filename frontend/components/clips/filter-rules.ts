import { ClipEntry } from "@/lib/types";
import { clipDurationSeconds, clipReady } from "@/components/clips/clip-ui-utils";

export type ClipSortOption =
  | "timeline-asc"
  | "score-desc"
  | "duration-asc"
  | "duration-desc"
  | "date-desc";

export type NumericOperator = "gte" | "gt" | "lte" | "lt" | "eq";

export type QuickFilterPreset = "best" | "newest" | "ready" | "short" | "medium" | "long";

export type FilterRule =
  | ScoreFilterRule
  | DurationFilterRule
  | StatusFilterRule
  | TagFilterRule;

export interface ScoreFilterRule {
  id: string;
  type: "score";
  operator: NumericOperator;
  value: number;
}

export interface DurationFilterRule {
  id: string;
  type: "duration";
  operator: NumericOperator;
  value: number;
}

export interface StatusFilterRule {
  id: string;
  type: "status";
  operator: "is" | "is-not";
  value: string;
}

export interface TagFilterRule {
  id: string;
  type: "tag";
  operator: "contains" | "is" | "quick";
  value: string;
}

export interface ClipsFilterState {
  query: string;
  rules: FilterRule[];
  sort: ClipSortOption;
}

export interface RuleMatchContext {
  newestIds: Set<string>;
}

interface PersistedRulePayload {
  type?: unknown;
  operator?: unknown;
  value?: unknown;
}

const BEST_SCORE_PERCENT = 82;
const SORT_VALUES: ClipSortOption[] = [
  "timeline-asc",
  "score-desc",
  "duration-asc",
  "duration-desc",
  "date-desc",
];
const NUMERIC_OPERATOR_VALUES: NumericOperator[] = ["gte", "gt", "lte", "lt", "eq"];
const STATUS_OPERATOR_VALUES: Array<StatusFilterRule["operator"]> = ["is", "is-not"];
const TAG_OPERATOR_VALUES: Array<TagFilterRule["operator"]> = ["contains", "is", "quick"];
const QUICK_PRESET_VALUES: QuickFilterPreset[] = ["best", "newest", "ready", "short", "medium", "long"];

export const SORT_OPTIONS: Array<{ value: ClipSortOption; label: string }> = [
  { value: "timeline-asc", label: "Timeline (early first)" },
  { value: "score-desc", label: "Score (high first)" },
  { value: "duration-asc", label: "Duration (short first)" },
  { value: "duration-desc", label: "Duration (long first)" },
  { value: "date-desc", label: "Date (newest first)" },
];

export const NUMERIC_OPERATOR_OPTIONS: Array<{ value: NumericOperator; label: string; symbol: string }> = [
  { value: "gte", label: "At least", symbol: ">=" },
  { value: "gt", label: "Greater than", symbol: ">" },
  { value: "lte", label: "At most", symbol: "<=" },
  { value: "lt", label: "Lower than", symbol: "<" },
  { value: "eq", label: "Equals", symbol: "=" },
];

export const STATUS_OPERATOR_OPTIONS: Array<{ value: StatusFilterRule["operator"]; label: string }> = [
  { value: "is", label: "Is" },
  { value: "is-not", label: "Is not" },
];

export const TAG_OPERATOR_OPTIONS: Array<{ value: TagFilterRule["operator"]; label: string }> = [
  { value: "contains", label: "Contains" },
  { value: "is", label: "Is exactly" },
  { value: "quick", label: "Quick preset" },
];

export const QUICK_PRESET_OPTIONS: Array<{ value: QuickFilterPreset; label: string }> = [
  { value: "best", label: "Best score" },
  { value: "newest", label: "Newest clips" },
  { value: "ready", label: "Ready clips" },
  { value: "short", label: "Short clips (<= 20s)" },
  { value: "medium", label: "Medium clips (20s-40s)" },
  { value: "long", label: "Long clips (> 40s)" },
];

export const DEFAULT_CLIPS_FILTER_STATE: ClipsFilterState = {
  query: "",
  rules: [],
  sort: "timeline-asc",
};

function createRuleId() {
  return `rule_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

function clampNumber(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function numericOperatorSymbol(operator: NumericOperator) {
  return NUMERIC_OPERATOR_OPTIONS.find((item) => item.value === operator)?.symbol ?? ">=";
}

function normalizeStatus(value?: string | null) {
  return (value ?? "").trim().toLowerCase();
}

function statusLabel(value: string) {
  const normalized = normalizeStatus(value);
  if (normalized === "ready") return "Ready";
  if (normalized === "not-ready") return "Not ready";
  if (!normalized) return "Unknown";
  return value.replace(/[-_]/g, " ");
}

function quickPresetLabel(value: string) {
  return QUICK_PRESET_OPTIONS.find((item) => item.value === value)?.label ?? "Quick";
}

export function createFilterRule(type: FilterRule["type"]): FilterRule {
  if (type === "score") {
    return {
      id: createRuleId(),
      type: "score",
      operator: "gte",
      value: 80,
    };
  }

  if (type === "duration") {
    return {
      id: createRuleId(),
      type: "duration",
      operator: "lt",
      value: 30,
    };
  }

  if (type === "status") {
    return {
      id: createRuleId(),
      type: "status",
      operator: "is",
      value: "ready",
    };
  }

  return {
    id: createRuleId(),
    type: "tag",
    operator: "quick",
    value: "best",
  };
}

export function coerceSortOption(value?: string | null): ClipSortOption {
  if (value && SORT_VALUES.includes(value as ClipSortOption)) {
    return value as ClipSortOption;
  }
  return DEFAULT_CLIPS_FILTER_STATE.sort;
}

export function hasActiveFilterState(state: ClipsFilterState) {
  return (
    state.query.trim().length > 0 ||
    state.rules.length > 0 ||
    state.sort !== DEFAULT_CLIPS_FILTER_STATE.sort
  );
}

export function formatRuleLabel(rule: FilterRule) {
  if (rule.type === "score") {
    return `Score ${numericOperatorSymbol(rule.operator)} ${rule.value}`;
  }

  if (rule.type === "duration") {
    return `Duration ${numericOperatorSymbol(rule.operator)} ${rule.value}s`;
  }

  if (rule.type === "status") {
    const prefix = rule.operator === "is-not" ? "Status is not" : "Status";
    return `${prefix}: ${statusLabel(rule.value)}`;
  }

  if (rule.operator === "quick") {
    return `Quick: ${quickPresetLabel(rule.value)}`;
  }

  if (rule.operator === "contains") {
    return `Tag contains: ${rule.value || "..."}`;
  }

  return `Tag: ${rule.value || "..."}`;
}

function compareNumeric(actual: number, operator: NumericOperator, expected: number) {
  if (operator === "gt") return actual > expected;
  if (operator === "gte") return actual >= expected;
  if (operator === "lt") return actual < expected;
  if (operator === "lte") return actual <= expected;
  return actual === expected;
}

function scorePercent(score?: number | null) {
  if (typeof score !== "number" || !Number.isFinite(score)) return 0;
  return score * 100;
}

function normalizeStatusForRule(value: string) {
  const normalized = normalizeStatus(value);
  if (!normalized) return "ready";
  return normalized;
}

function matchesQuickPreset(clip: ClipEntry, preset: string, context: RuleMatchContext) {
  const duration = clipDurationSeconds(clip);

  if (preset === "best") return scorePercent(clip.score) >= BEST_SCORE_PERCENT;
  if (preset === "newest") return context.newestIds.has(clip.id);
  if (preset === "ready") return clipReady(clip.status);
  if (preset === "short") return duration <= 20;
  if (preset === "medium") return duration > 20 && duration <= 40;
  if (preset === "long") return duration > 40;
  return true;
}

export function matchesRule(clip: ClipEntry, rule: FilterRule, context: RuleMatchContext) {
  if (rule.type === "score") {
    return compareNumeric(scorePercent(clip.score), rule.operator, rule.value);
  }

  if (rule.type === "duration") {
    return compareNumeric(clipDurationSeconds(clip), rule.operator, rule.value);
  }

  if (rule.type === "status") {
    const normalizedValue = normalizeStatusForRule(rule.value);
    const matches =
      normalizedValue === "ready"
        ? clipReady(clip.status)
        : normalizedValue === "not-ready"
          ? !clipReady(clip.status)
          : normalizeStatus(clip.status) === normalizedValue;

    return rule.operator === "is-not" ? !matches : matches;
  }

  if (rule.operator === "quick") {
    return matchesQuickPreset(clip, rule.value, context);
  }

  const clipTag = (clip.tag ?? "").trim().toLowerCase();
  const target = rule.value.trim().toLowerCase();
  if (!target) return true;

  if (rule.operator === "contains") {
    return clipTag.includes(target);
  }

  return clipTag === target;
}

export function serializeRules(rules: FilterRule[]) {
  if (rules.length === 0) return "";
  const payload = rules.map(({ id: _id, ...rule }) => rule);
  return JSON.stringify(payload);
}

function toNumber(value: unknown) {
  const numericValue = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(numericValue)) return null;
  return numericValue;
}

function toStringValue(value: unknown) {
  if (typeof value !== "string") return "";
  return value.trim();
}

function parseScoreRule(payload: PersistedRulePayload): ScoreFilterRule | null {
  const operator = payload.operator;
  const value = toNumber(payload.value);
  if (!NUMERIC_OPERATOR_VALUES.includes(operator as NumericOperator) || value == null) return null;

  return {
    id: createRuleId(),
    type: "score",
    operator: operator as NumericOperator,
    value: Math.round(clampNumber(value, 0, 100)),
  };
}

function parseDurationRule(payload: PersistedRulePayload): DurationFilterRule | null {
  const operator = payload.operator;
  const value = toNumber(payload.value);
  if (!NUMERIC_OPERATOR_VALUES.includes(operator as NumericOperator) || value == null) return null;

  return {
    id: createRuleId(),
    type: "duration",
    operator: operator as NumericOperator,
    value: Math.round(clampNumber(value, 0, 7200)),
  };
}

function parseStatusRule(payload: PersistedRulePayload): StatusFilterRule | null {
  const operator = payload.operator;
  const value = toStringValue(payload.value);
  if (!STATUS_OPERATOR_VALUES.includes(operator as StatusFilterRule["operator"]) || !value) return null;

  return {
    id: createRuleId(),
    type: "status",
    operator: operator as StatusFilterRule["operator"],
    value: normalizeStatusForRule(value),
  };
}

function parseTagRule(payload: PersistedRulePayload): TagFilterRule | null {
  const operator = payload.operator;
  const value = toStringValue(payload.value);
  if (!TAG_OPERATOR_VALUES.includes(operator as TagFilterRule["operator"])) return null;

  if ((operator === "is" || operator === "contains") && !value) return null;
  if (operator === "quick" && !QUICK_PRESET_VALUES.includes(value as QuickFilterPreset)) return null;

  return {
    id: createRuleId(),
    type: "tag",
    operator: operator as TagFilterRule["operator"],
    value,
  };
}

export function deserializeRules(serialized?: string | null): FilterRule[] {
  if (!serialized) return [];

  try {
    const parsed = JSON.parse(serialized);
    if (!Array.isArray(parsed)) return [];

    return parsed.reduce<FilterRule[]>((collection, item) => {
      const payload = item as PersistedRulePayload;
      const type = payload.type;
      if (type === "score") {
        const rule = parseScoreRule(payload);
        if (rule) collection.push(rule);
      } else if (type === "duration") {
        const rule = parseDurationRule(payload);
        if (rule) collection.push(rule);
      } else if (type === "status") {
        const rule = parseStatusRule(payload);
        if (rule) collection.push(rule);
      } else if (type === "tag") {
        const rule = parseTagRule(payload);
        if (rule) collection.push(rule);
      }

      return collection;
    }, []);
  } catch {
    return [];
  }
}

export function getFilterTypeLabel(type: FilterRule["type"]) {
  if (type === "score") return "Score";
  if (type === "duration") return "Duration";
  if (type === "status") return "Status";
  return "Tag / Quick";
}
