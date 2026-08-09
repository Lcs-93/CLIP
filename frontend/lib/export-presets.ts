export interface ExportPresetOption {
  id: string;
  label: string;
  ratioLabel: string;
  aspectRatio: number;
  objectFit: "cover" | "contain";
}

export const EXPORT_PRESETS: ExportPresetOption[] = [
  { id: "9x16-crop", label: "9:16", ratioLabel: "9:16", aspectRatio: 9 / 16, objectFit: "cover" },
  { id: "4x5-crop", label: "4:5", ratioLabel: "4:5", aspectRatio: 4 / 5, objectFit: "cover" },
  { id: "1x1-crop", label: "1:1", ratioLabel: "1:1", aspectRatio: 1, objectFit: "cover" },
  { id: "1x1-fit", label: "1:1 Fit", ratioLabel: "1:1", aspectRatio: 1, objectFit: "contain" },
  { id: "16x9-fit", label: "16:9", ratioLabel: "16:9", aspectRatio: 16 / 9, objectFit: "contain" },
];

export const DEFAULT_EXPORT_PRESET_ID = EXPORT_PRESETS[0].id;

