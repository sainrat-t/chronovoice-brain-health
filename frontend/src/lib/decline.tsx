// How a marker moves with decline, per the literature (MarkerSpec.decline_direction).
import { ArrowDown, ArrowUp, Minus, type LucideIcon } from "lucide-react";
import type { MarkerSpec } from "../api/types";

export const DECLINE: Record<MarkerSpec["decline_direction"], { icon: LucideIcon; text: string }> = {
  increase: { icon: ArrowUp, text: "Higher values point toward decline" },
  decrease: { icon: ArrowDown, text: "Lower values point toward decline" },
  uncertain: { icon: Minus, text: "Direction linked to decline not established" },
};
