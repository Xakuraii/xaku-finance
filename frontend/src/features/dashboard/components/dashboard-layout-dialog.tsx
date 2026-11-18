import React, { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowUp, ArrowDown, Check, X, RotateCcw, LayoutDashboard } from "lucide-react";
import { WidgetLayoutItem } from "../api/dashboard-api";

interface DashboardLayoutDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentLayout: WidgetLayoutItem[];
  onSave: (widgets: WidgetLayoutItem[]) => Promise<void>;
  onReset: () => Promise<void>;
}

export const DashboardLayoutDialog: React.FC<DashboardLayoutDialogProps> = ({
  open,
  onOpenChange,
  currentLayout,
  onSave,
  onReset,
}) => {
  const [widgets, setWidgets] = useState<WidgetLayoutItem[]>(currentLayout);
  const [isSaving, setIsSaving] = useState(false);
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => {
    if (open) {
      setWidgets([...currentLayout]);
    }
  }, [open, currentLayout]);

  const moveWidget = (index: number, direction: "up" | "down") => {
    const targetIndex = direction === "up" ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= widgets.length) return;

    const newWidgets = [...widgets];
    const [moved] = newWidgets.splice(index, 1);
    newWidgets.splice(targetIndex, 0, moved);
    setWidgets(newWidgets);
  };

  const toggleWidget = (index: number) => {
    const newWidgets = [...widgets];
    newWidgets[index] = {
      ...newWidgets[index],
      enabled: !newWidgets[index].enabled,
    };
    setWidgets(newWidgets);
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      await onSave(widgets);
      onOpenChange(false);
    } finally {
      setIsSaving(false);
    }
  };

  const handleReset = async () => {
    try {
      setIsResetting(true);
      await onReset();
      onOpenChange(false);
    } finally {
      setIsResetting(false);
    }
  };

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50 animate-in fade-in" />
        <Dialog.Content
          className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-card text-card-foreground p-6 rounded-xl shadow-xl z-50 border border-border animate-in zoom-in-95 duration-150"
          aria-describedby="customize-dashboard-description"
        >
          <div className="flex items-center justify-between pb-3 border-b border-border">
            <div className="flex items-center gap-2">
              <LayoutDashboard className="w-5 h-5 text-primary" />
              <Dialog.Title className="text-lg font-semibold">Customize Dashboard</Dialog.Title>
            </div>
            <Dialog.Close className="p-1 rounded-md text-muted-foreground hover:bg-muted focus:ring-2 focus:ring-ring">
              <X className="w-5 h-5" />
            </Dialog.Close>
          </div>

          <p id="customize-dashboard-description" className="text-xs text-muted-foreground mt-2">
            Reorder widgets or toggle their visibility. Changes are saved across your devices.
          </p>

          <div className="mt-4 max-h-[380px] overflow-y-auto space-y-2 pr-1">
            {widgets.map((widget, idx) => (
              <div
                key={widget.key}
                className={`flex items-center justify-between p-2.5 rounded-lg border transition-colors ${
                  widget.enabled
                    ? "bg-accent/30 border-border"
                    : "bg-muted/40 border-muted opacity-60"
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <button
                    type="button"
                    role="checkbox"
                    aria-checked={widget.enabled}
                    onClick={() => toggleWidget(idx)}
                    className={`w-5 h-5 rounded flex items-center justify-center border transition-colors ${
                      widget.enabled
                        ? "bg-primary border-primary text-primary-foreground"
                        : "border-muted-foreground bg-background"
                    }`}
                    title={widget.enabled ? "Hide widget" : "Show widget"}
                  >
                    {widget.enabled && <Check className="w-3.5 h-3.5" />}
                  </button>
                  <span className="text-sm font-medium">{widget.title || widget.key}</span>
                </div>

                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    onClick={() => moveWidget(idx, "up")}
                    disabled={idx === 0}
                    className="p-1 rounded hover:bg-muted text-muted-foreground disabled:opacity-30 disabled:pointer-events-none"
                    aria-label={`Move ${widget.title || widget.key} up`}
                  >
                    <ArrowUp className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => moveWidget(idx, "down")}
                    disabled={idx === widgets.length - 1}
                    className="p-1 rounded hover:bg-muted text-muted-foreground disabled:opacity-30 disabled:pointer-events-none"
                    aria-label={`Move ${widget.title || widget.key} down`}
                  >
                    <ArrowDown className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 pt-3 border-t border-border flex items-center justify-between gap-3">
            <button
              type="button"
              onClick={handleReset}
              disabled={isResetting || isSaving}
              className="px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground flex items-center gap-1.5 rounded hover:bg-muted transition-colors"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              Reset to defaults
            </button>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => onOpenChange(false)}
                className="px-3 py-1.5 text-xs font-medium border border-border rounded-lg hover:bg-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSave}
                disabled={isSaving || isResetting}
                className="px-4 py-1.5 text-xs font-medium bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50"
              >
                {isSaving ? "Saving..." : "Save Layout"}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
