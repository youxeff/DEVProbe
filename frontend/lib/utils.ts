import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
export function number(value: number | null | undefined) {
  return (value ?? 0).toLocaleString();
}
export function date(value: string) {
  return new Date(value).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
export function duration(value: number | null) {
  return value == null ? "—" : `${value.toFixed(1)}s`;
}
