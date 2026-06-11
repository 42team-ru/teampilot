import { useEffect } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { useAppStore } from "@/stores/appStore";
import { getTgUser, tg } from "@/lib/tg";
import { Router } from "@/router";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false },
  },
});

type Rgb = [number, number, number];

const LIGHT_DEFAULTS = {
  background: "#f8fafc",
  foreground: "#0f172a",
  primary: "#229ed9",
  primaryForeground: "#ffffff",
  hint: "#64748b",
  destructive: "#dc2626",
};

const DARK_DEFAULTS = {
  background: "#0f172a",
  foreground: "#f8fafc",
  primary: "#38bdf8",
  primaryForeground: "#ffffff",
  hint: "#94a3b8",
  destructive: "#f87171",
};

function applyTelegramTheme() {
  const scheme = tg?.colorScheme ?? "light";
  document.documentElement.classList.remove("light", "dark");
  document.documentElement.classList.add(scheme);
  applyTelegramThemeParams(scheme);
}

function applyTelegramThemeParams(scheme: "light" | "dark") {
  const root = document.documentElement;
  const params = tg?.themeParams ?? {};
  const defaults = scheme === "dark" ? DARK_DEFAULTS : LIGHT_DEFAULTS;

  const background = readColor(params.bg_color, defaults.background);
  const foreground = readColor(params.text_color, defaults.foreground);
  const primary = readColor(params.button_color, defaults.primary);
  const primaryForeground = readColor(params.button_text_color, defaults.primaryForeground);
  const hint = readColor(params.hint_color, defaults.hint);
  const link = readColor(params.link_color, defaults.primary);
  const destructive = readColor(params.destructive_text_color, defaults.destructive);
  const telegramSecondary = parseHexColor(params.secondary_bg_color);

  const card = surfaceColor(background, telegramSecondary, primary, scheme === "dark" ? 0.18 : 0.10);
  const secondary = surfaceColor(background, telegramSecondary, primary, scheme === "dark" ? 0.24 : 0.15);
  const muted = surfaceColor(background, telegramSecondary, primary, scheme === "dark" ? 0.14 : 0.08);
  const accent = surfaceColor(background, telegramSecondary, primary, scheme === "dark" ? 0.30 : 0.20);
  const border = mix(background, foreground, scheme === "dark" ? 0.24 : 0.18);

  setHslVar(root, "background", background);
  setHslVar(root, "foreground", foreground);
  setHslVar(root, "card", card);
  setHslVar(root, "card-foreground", foreground);
  setHslVar(root, "popover", card);
  setHslVar(root, "popover-foreground", foreground);
  setHslVar(root, "primary", primary);
  setHslVar(root, "primary-foreground", primaryForeground);
  setHslVar(root, "secondary", secondary);
  setHslVar(root, "secondary-foreground", foreground);
  setHslVar(root, "muted", muted);
  setHslVar(root, "muted-foreground", hint);
  setHslVar(root, "accent", accent);
  setHslVar(root, "accent-foreground", link);
  setHslVar(root, "destructive", destructive);
  setHslVar(root, "destructive-foreground", primaryForeground);
  setHslVar(root, "border", border);
  setHslVar(root, "input", border);
  setHslVar(root, "ring", primary);
}

function surfaceColor(background: Rgb, candidate: Rgb | null, tint: Rgb, tintAmount: number): Rgb {
  if (candidate && contrastRatio(background, candidate) >= 1.12) {
    return candidate;
  }
  return mix(background, tint, tintAmount);
}

function readColor(value: string | undefined, fallback: string): Rgb {
  return parseHexColor(value) ?? parseHexColor(fallback) ?? [0, 0, 0];
}

function parseHexColor(value: string | undefined): Rgb | null {
  if (!value) return null;
  const hex = value.trim().replace(/^#/, "");
  if (!/^[\da-f]{6}$/i.test(hex)) return null;
  return [
    Number.parseInt(hex.slice(0, 2), 16),
    Number.parseInt(hex.slice(2, 4), 16),
    Number.parseInt(hex.slice(4, 6), 16),
  ];
}

function mix(a: Rgb, b: Rgb, amount: number): Rgb {
  return [
    Math.round(a[0] + (b[0] - a[0]) * amount),
    Math.round(a[1] + (b[1] - a[1]) * amount),
    Math.round(a[2] + (b[2] - a[2]) * amount),
  ];
}

function setHslVar(root: HTMLElement, name: string, rgb: Rgb) {
  const [h, s, l] = rgbToHsl(rgb);
  root.style.setProperty(`--${name}`, `${Math.round(h)} ${Math.round(s)}% ${Math.round(l)}%`);
}

function rgbToHsl([r, g, b]: Rgb): [number, number, number] {
  r /= 255;
  g /= 255;
  b /= 255;

  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const delta = max - min;
  const lightness = (max + min) / 2;

  if (delta === 0) {
    return [0, 0, lightness * 100];
  }

  const saturation = delta / (1 - Math.abs(2 * lightness - 1));
  let hue = 0;
  if (max === r) {
    hue = ((g - b) / delta) % 6;
  } else if (max === g) {
    hue = (b - r) / delta + 2;
  } else {
    hue = (r - g) / delta + 4;
  }
  hue *= 60;
  if (hue < 0) hue += 360;

  return [hue, saturation * 100, lightness * 100];
}

function contrastRatio(a: Rgb, b: Rgb): number {
  const light = relativeLuminance(a);
  const dark = relativeLuminance(b);
  const [lighter, darker] = light > dark ? [light, dark] : [dark, light];
  return (lighter + 0.05) / (darker + 0.05);
}

function relativeLuminance(rgb: Rgb): number {
  const [r, g, b] = rgb.map((channel) => {
    const value = channel / 255;
    return value <= 0.03928 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export default function App() {
  const setTgUser = useAppStore((s) => s.setTgUser);

  useEffect(() => {
    tg?.ready();
    tg?.expand();

    const user = getTgUser();
    if (user) setTgUser(user);

    applyTelegramTheme();
    tg?.onEvent("themeChanged", applyTelegramTheme);

    return () => {
      tg?.offEvent("themeChanged", applyTelegramTheme);
    };
  }, [setTgUser]);

  return (
    <QueryClientProvider client={queryClient}>
      <Router />
      <Toaster position="top-center" richColors />
    </QueryClientProvider>
  );
}
