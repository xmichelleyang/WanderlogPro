"""Generate a self-contained HTML trip guide from a Guide object."""

from __future__ import annotations

import html
import os
from datetime import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from wanderlogpro.offline_mode.models import Guide, GuideDay, GuideFlight, GuideHotel, GuidePlace


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------


def _css() -> str:
    """Return all CSS for the guide."""
    return """\
:root {
  --primary: #4338CA;
  --accent-warm: #F59E0B;
  --accent-hot: #F97316;
  --surface-light: #FFFBF5;
  --surface-dark: #0F172A;
  --text: #1C1917;
  --text-dark: #FEF3C7;
  --muted: #78716C;
  --radius: 1rem;
  --spring: cubic-bezier(0.34, 1.56, 0.64, 1);
  --cat-food: #F59E0B;
  --cat-snack: #EC4899;
  --cat-activity: #4338CA;
  --cat-flight: #F97316;
  --cat-hotel: #0D9488;
  --font-display: 'Fraunces', serif;
  --font-body: 'Geist', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html {
  scroll-behavior: smooth;
  -webkit-text-size-adjust: 100%;
}

body {
  font-family: var(--font-body);
  background: var(--surface-light);
  color: var(--text);
  line-height: 1.6;
  min-height: 100dvh;
  padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left);
  transition: background 300ms ease, color 300ms ease;
}

body.dark {
  background: var(--surface-dark);
  color: var(--text-dark);
}

.container {
  max-width: 600px;
  margin: 0 auto;
  padding: 1rem;
}

/* Typography */
h1, h2, h3 { font-family: var(--font-display); font-weight: 600; }
.micro-label {
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-size: 0.7rem;
  color: var(--muted);
}
body.dark .micro-label { color: #a8a29e; }

/* Hero */
.hero {
  text-align: center;
  padding: 3rem 1rem 2rem;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(67,56,202,0.15) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(245,158,11,0.12) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(249,115,22,0.10) 0%, transparent 50%);
  border-radius: var(--radius);
  margin-bottom: 1.5rem;
  animation: heroIn 0.8s var(--spring) both;
}
body.dark .hero {
  background:
    radial-gradient(ellipse at 20% 50%, rgba(67,56,202,0.25) 0%, transparent 50%),
    radial-gradient(ellipse at 80% 20%, rgba(245,158,11,0.18) 0%, transparent 50%),
    radial-gradient(ellipse at 50% 80%, rgba(249,115,22,0.15) 0%, transparent 50%);
}
.hero h1 { font-size: 2rem; margin-bottom: 0.5rem; }
.hero .subtitle { color: var(--muted); font-size: 0.9rem; }
body.dark .hero .subtitle { color: #a8a29e; }

/* Glass cards — section wrappers */
.glass-card {
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-radius: var(--radius);
  padding: 1.25rem;
  margin-bottom: 1rem;
  border: 1px solid rgba(0,0,0,0.06);
  animation: fadeSlideUp 0.6s var(--spring) both;
}
body.dark .glass-card {
  background: rgba(15,23,42,0.7);
  border-color: rgba(255,255,255,0.08);
}
.glass-card h2 { font-size: 1.1rem; margin-bottom: 0.75rem; }

/* ====== Section Tabs (Option C rounded bar + V2 ambient glow) ====== */
.sec-tabs {
  display: flex;
  background: rgba(255,255,255,0.85);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  margin-bottom: 1rem;
  position: sticky;
  top: 0;
  z-index: 20;
}
body.dark .sec-tabs {
  background: rgba(15,23,42,0.85);
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
}
.sec-tab {
  flex: 1;
  padding: 0.65rem 0;
  text-align: center;
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  border: none;
  background: transparent;
  color: var(--muted);
  border-bottom: 2px solid transparent;
  font-family: var(--font-body);
  transition: all 0.2s ease;
  min-height: 44px;
}
body.dark .sec-tab { color: #a8a29e; }
.sec-tab:hover { background: rgba(0,0,0,0.02); }
body.dark .sec-tab:hover { background: rgba(255,255,255,0.04); }
.sec-tab.active-itin { color: #0D9488; background: rgba(13,148,136,0.06); }
body.dark .sec-tab.active-itin { color: #2DD4BF; background: rgba(13,148,136,0.12); }
.sec-tab.active-hotel { color: var(--primary); background: rgba(67,56,202,0.06); }
body.dark .sec-tab.active-hotel { color: #a5b4fc; background: rgba(67,56,202,0.12); }
.sec-tab.active-flight { color: var(--accent-hot); background: rgba(234,88,12,0.06); }
body.dark .sec-tab.active-flight { color: #fb923c; background: rgba(234,88,12,0.12); }

.sec-panel { display: none; }
.sec-panel.active { display: block; animation: fadeSlideUp 0.3s ease both; }

/* Ambient glow behind content */
.content-area {
  position: relative;
  min-height: 200px;
}
.content-area::before {
  content: '';
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.4s ease;
  border-radius: var(--radius);
}
.content-area.glow-itin::before {
  opacity: 0.5;
  background: radial-gradient(ellipse at 50% 0%, rgba(13,148,136,0.1) 0%, transparent 60%);
}
.content-area.glow-hotel::before {
  opacity: 0.5;
  background: radial-gradient(ellipse at 50% 0%, rgba(67,56,202,0.1) 0%, transparent 60%);
}
.content-area.glow-flight::before {
  opacity: 0.5;
  background: radial-gradient(ellipse at 50% 0%, rgba(234,88,12,0.1) 0%, transparent 60%);
}
body.dark .content-area.glow-itin::before {
  background: radial-gradient(ellipse at 50% 0%, rgba(13,148,136,0.15) 0%, transparent 60%);
}
body.dark .content-area.glow-hotel::before {
  background: radial-gradient(ellipse at 50% 0%, rgba(67,56,202,0.15) 0%, transparent 60%);
}
body.dark .content-area.glow-flight::before {
  background: radial-gradient(ellipse at 50% 0%, rgba(234,88,12,0.15) 0%, transparent 60%);
}
.content-area > * { position: relative; z-index: 1; }

/* Section sub-header with count badge */
.sec-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}
.sec-header h2 { font-size: 1.1rem; margin-bottom: 0; }
.sec-count {
  font-size: 0.65rem;
  font-weight: 600;
  padding: 0.2rem 0.65rem;
  border-radius: 2rem;
}
.sec-count.cnt-itin { background: rgba(13,148,136,0.1); color: #0D9488; }
body.dark .sec-count.cnt-itin { background: rgba(13,148,136,0.2); color: #2DD4BF; }
.sec-count.cnt-hotel { background: rgba(67,56,202,0.1); color: var(--primary); }
body.dark .sec-count.cnt-hotel { background: rgba(67,56,202,0.2); color: #a5b4fc; }
.sec-count.cnt-flight { background: rgba(234,88,12,0.1); color: #ea580c; }
body.dark .sec-count.cnt-flight { background: rgba(234,88,12,0.2); color: #fb923c; }

/* Boarding pass cards — always expanded in section tabs */
.bp-card {
  border-radius: 0.75rem;
  overflow: hidden;
  margin-bottom: 0.6rem;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
  border: 1px solid rgba(0,0,0,0.05);
}
body.dark .bp-card {
  box-shadow: 0 1px 4px rgba(0,0,0,0.2);
  border-color: rgba(255,255,255,0.08);
}
.bp-header {
  display: flex;
  align-items: center;
  padding: 0.6rem 0.85rem;
  gap: 0.65rem;
  background: linear-gradient(135deg, #ea580c 0%, #fb923c 100%);
  color: white;
}
.bp-card.bp-hotel .bp-header {
  background: linear-gradient(135deg, #4338CA 0%, #818cf8 100%);
}
.bp-header .bp-route { font-weight: 800; font-size: 0.95rem; letter-spacing: 0.03em; }
.bp-header .bp-airline-tag { font-size: 0.68rem; opacity: 0.8; font-weight: 400; }
.bp-body {
  background: white;
}
body.dark .bp-body { background: rgba(15,23,42,0.9); }
.bp-columns {
  display: flex;
  padding: 0.85rem 1rem;
  gap: 0;
}
.bp-col { flex: 1; }
.bp-col + .bp-col {
  border-left: 1px dashed rgba(0,0,0,0.1);
  padding-left: 0.85rem;
}
body.dark .bp-col + .bp-col { border-left-color: rgba(255,255,255,0.1); }
.bp-label {
  font-size: 0.6rem;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--muted);
  font-weight: 600;
  margin-bottom: 0.1rem;
}
body.dark .bp-label { color: #a8a29e; }
.bp-val { font-size: 0.9rem; font-weight: 700; color: var(--text); }
body.dark .bp-val { color: var(--text-dark); }
.bp-val-sub { font-size: 0.75rem; color: var(--text); margin-top: 0.05rem; }
body.dark .bp-val-sub { color: var(--text-dark); }
.bp-val-muted { font-size: 0.7rem; color: var(--muted); margin-top: 0.15rem; }
body.dark .bp-val-muted { color: #a8a29e; }
.bp-conf-strip {
  background: #faf5ee;
  border-top: 1px dashed rgba(0,0,0,0.08);
  padding: 0.4rem 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.73rem;
  color: var(--muted);
}
body.dark .bp-conf-strip {
  background: rgba(30,41,59,0.8);
  border-top-color: rgba(255,255,255,0.08);
  color: #a8a29e;
}
.bp-card.bp-hotel .bp-conf-strip { background: #f0eef9; }
body.dark .bp-card.bp-hotel .bp-conf-strip { background: rgba(30,30,60,0.8); }
.bp-conf-code {
  font-weight: 700;
  color: var(--text);
  font-family: 'Consolas', 'SF Mono', monospace;
  letter-spacing: 0.06em;
  font-size: 0.78rem;
}
body.dark .bp-conf-code { color: var(--text-dark); }

/* Day-view flight card in itinerary (always expanded, no interaction) */
.bp-card.bp-day-card .bp-header { cursor: default; }

/* Tabs — sticky within itinerary panel */
.tab-bar {
  display: flex;
  gap: 0.5rem;
  overflow-x: auto;
  padding: 0.5rem 0.75rem;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  position: sticky;
  top: 0;
  z-index: 20;
  background: rgba(255,251,245,0.92);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}
.tab-bar.centered {
  justify-content: center;
}
.tab-bar::-webkit-scrollbar { display: none; }
.tab-pill {
  flex-shrink: 0;
  padding: 0.5rem 1rem;
  border-radius: 2rem;
  border: none;
  background: rgba(0,0,0,0.05);
  font-family: var(--font-body);
  font-size: 0.8rem;
  cursor: pointer;
  min-height: 44px;
  min-width: 44px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  transition: all 300ms var(--spring);
}
body.dark .tab-pill { background: rgba(255,255,255,0.08); color: var(--text-dark); }
body.dark .tab-bar { background: rgba(30,30,30,0.92); }
.tab-pill.active {
  background: linear-gradient(135deg, var(--primary), var(--accent-hot));
  color: #fff;
  transform: scale(1.05);
}
body.dark .tab-pill.active {
  background: linear-gradient(135deg, var(--primary), var(--accent-hot));
  color: #fff;
}
.tab-pill .day-label { font-weight: 600; }
.tab-pill .day-date { font-size: 0.65rem; opacity: 0.8; }

/* Scroll progress dots */
.scroll-dots {
  display: flex;
  justify-content: center;
  gap: 4px;
  padding: 0.5rem 0 0.75rem;
}
.scroll-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: rgba(0,0,0,0.12);
  transition: all 300ms ease;
}
body.dark .scroll-dot { background: rgba(255,255,255,0.15); }
.scroll-dot.dot-active {
  width: 18px;
  border-radius: 3px;
  background: linear-gradient(135deg, var(--primary), var(--accent-hot));
}
body.dark .scroll-dot.dot-active {
  background: linear-gradient(135deg, var(--primary), var(--accent-hot));
}

/* Day carousel — horizontal snap scroll */
.day-carousel {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.day-carousel::-webkit-scrollbar { display: none; }

/* Day panels — full-width snap pages */
.day-panel {
  min-width: 100%;
  flex: 0 0 100%;
  scroll-snap-align: start;
  overflow-y: auto;
  padding: 0 0.75rem;
  box-sizing: border-box;
}

/* V6 Full Glow Connector place cards */
.place-card {
  width: 100%;
  position: relative;
  overflow: hidden;
  background: rgba(255,255,255,0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  border-radius: var(--radius);
  padding: 1rem;
  margin-bottom: 0;
  border: 1px solid rgba(255,255,255,0.35);
  transition: transform 200ms var(--spring), box-shadow 200ms ease;
  animation: fadeSlideUp 0.5s var(--spring) both;
}
body.dark .place-card {
  background: rgba(30,41,59,0.6);
  border-color: rgba(255,255,255,0.06);
}
.place-card:hover, .place-card:active {
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(67,56,202,0.1);
}

/* Left accent bar — gradient, full height */
.place-card::before {
  content: '';
  position: absolute;
  left: 0; top: 0; bottom: 0;
  width: 4px;
  border-radius: 2px 0 0 2px;
  background: linear-gradient(to bottom, var(--cat-activity), rgba(67,56,202,0.3));
}
.place-card.cat-food::before { background: linear-gradient(to bottom, var(--cat-food), rgba(245,158,11,0.3)); }
.place-card.cat-snack::before { background: linear-gradient(to bottom, var(--cat-snack), rgba(236,72,153,0.3)); }
.place-card.cat-activity::before { background: linear-gradient(to bottom, var(--cat-activity), rgba(67,56,202,0.3)); }
.place-card.cat-flight::before { background: linear-gradient(to bottom, var(--cat-flight), rgba(249,115,22,0.3)); }
.place-card.cat-hotel::before { background: linear-gradient(to bottom, var(--cat-hotel), rgba(13,148,136,0.3)); }

/* Top row: icon + info */
.place-top { display: flex; gap: 0.65rem; align-items: start; }

/* Icon badge — rounded square with ::after glow halo */
.place-badge {
  width: 40px; height: 40px; border-radius: 12px; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  font-size: 1.1rem; position: relative;
  background: rgba(67,56,202,0.08);
}
.cat-food .place-badge { background: rgba(245,158,11,0.12); }
.cat-snack .place-badge { background: rgba(236,72,153,0.12); }
.cat-hotel .place-badge { background: rgba(13,148,136,0.1); }
.cat-flight .place-badge { background: rgba(249,115,22,0.12); }
body.dark .place-badge { background: rgba(67,56,202,0.2); }
body.dark .cat-food .place-badge { background: rgba(245,158,11,0.2); }
body.dark .cat-snack .place-badge { background: rgba(236,72,153,0.2); }
body.dark .cat-hotel .place-badge { background: rgba(13,148,136,0.2); }
body.dark .cat-flight .place-badge { background: rgba(249,115,22,0.2); }
.place-badge::after {
  content: ''; position: absolute; inset: -2px; border-radius: 14px; opacity: 0.5;
}
.cat-activity .place-badge::after { box-shadow: 0 0 12px rgba(67,56,202,0.2); }
.cat-food .place-badge::after { box-shadow: 0 0 12px rgba(245,158,11,0.2); }
.cat-snack .place-badge::after { box-shadow: 0 0 12px rgba(236,72,153,0.2); }
.cat-hotel .place-badge::after { box-shadow: 0 0 12px rgba(13,148,136,0.2); }
.cat-flight .place-badge::after { box-shadow: 0 0 12px rgba(249,115,22,0.2); }

/* Card info (right of badge) */
.place-body { flex: 1; min-width: 0; }
.place-row { display: flex; justify-content: space-between; align-items: center; }
.place-body h3 { font-size: 0.92rem; }
.place-time {
  font-size: 0.75rem; font-weight: 700;
  background: linear-gradient(135deg, var(--primary), var(--accent-hot));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  background-clip: text; white-space: nowrap;
}
.place-time .t-sep {
  font-size: 0.62rem; font-weight: 500;
  -webkit-text-fill-color: var(--muted); background: none;
  margin: 0 0.1rem;
}
.place-body .address {
  font-size: 0.7rem;
  color: var(--muted);
  text-decoration: none;
  display: block;
  margin-top: 0.05rem;
}
.place-body .address:hover { text-decoration: underline; }
body.dark .place-body .address { color: #a8a29e; }
.place-body .notes { font-size: 0.78rem; color: var(--muted); margin-top: 0.25rem; }
body.dark .place-body .notes { color: #a8a29e; }
.place-body .place-desc {
  font-size: 0.68rem; color: var(--muted); margin-top: 0.3rem;
  line-height: 1.45; font-style: italic;
}
body.dark .place-body .place-desc { color: #a8a29e; }

/* Tag pills row — outside .place-top */
.place-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.3rem;
  margin-top: 0.4rem;
}
.place-tag {
  font-size: 0.58rem;
  font-weight: 600;
  padding: 0.12rem 0.45rem;
  border-radius: 1rem;
  background: rgba(67,56,202,0.08);
  color: var(--primary);
}
body.dark .place-tag { background: rgba(67,56,202,0.2); color: #a5b4fc; }
.place-tag.tag-food { background: rgba(245,158,11,0.1); color: var(--cat-food); }
body.dark .place-tag.tag-food { background: rgba(245,158,11,0.2); color: #FCD34D; }
.place-tag.tag-snack { background: rgba(236,72,153,0.1); color: var(--cat-snack); }
body.dark .place-tag.tag-snack { background: rgba(236,72,153,0.2); color: #F9A8D4; }
.place-tag.tag-hotel { background: rgba(13,148,136,0.1); color: var(--cat-hotel); }
body.dark .place-tag.tag-hotel { background: rgba(13,148,136,0.2); color: #5EEAD4; }
.place-tag.tag-dur { background: rgba(0,0,0,0.04); color: var(--muted); }
body.dark .place-tag.tag-dur { background: rgba(255,255,255,0.06); color: #a8a29e; }
/* Explicit duration tags — colored to match card category */
.place-tag.tag-dur-explicit { font-weight: 700; }
.cat-activity .place-tag.tag-dur-explicit { background: rgba(67,56,202,0.10); color: var(--cat-activity); }
body.dark .cat-activity .place-tag.tag-dur-explicit { background: rgba(67,56,202,0.2); color: #a5b4fc; }
.cat-food .place-tag.tag-dur-explicit { background: rgba(245,158,11,0.12); color: var(--cat-food); }
body.dark .cat-food .place-tag.tag-dur-explicit { background: rgba(245,158,11,0.2); color: #FCD34D; }
.cat-snack .place-tag.tag-dur-explicit { background: rgba(236,72,153,0.12); color: var(--cat-snack); }
body.dark .cat-snack .place-tag.tag-dur-explicit { background: rgba(236,72,153,0.2); color: #F9A8D4; }
.cat-hotel .place-tag.tag-dur-explicit { background: rgba(13,148,136,0.12); color: var(--cat-hotel); }
body.dark .cat-hotel .place-tag.tag-dur-explicit { background: rgba(13,148,136,0.2); color: #5EEAD4; }
.cat-flight .place-tag.tag-dur-explicit { background: rgba(249,115,22,0.12); color: var(--cat-flight); }
body.dark .cat-flight .place-tag.tag-dur-explicit { background: rgba(249,115,22,0.2); color: #FDBA74; }
/* Duration key footnote */
.duration-key {
  text-align: center;
  font-size: 0.62rem;
  color: var(--muted);
  opacity: 0.7;
  line-height: 1.6;
  margin-top: 1.5rem;
  padding-bottom: 0.5rem;
}
.duration-key .dk-pill {
  font-size: 0.52rem;
  font-weight: 600;
  padding: 0.1rem 0.4rem;
  border-radius: 1rem;
  vertical-align: middle;
}
.duration-key .dk-gray { background: rgba(0,0,0,0.04); color: var(--muted); }
body.dark .duration-key .dk-gray { background: rgba(255,255,255,0.06); color: #a8a29e; }
.duration-key .dk-colored { background: rgba(67,56,202,0.10); color: var(--cat-activity); }
body.dark .duration-key .dk-colored { background: rgba(67,56,202,0.2); color: #a5b4fc; }

/* Connector between cards — single glow line + gradient chip */
.connector {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.15rem 0;
  margin-left: 1.25rem;
}
.connector-line {
  width: 3px; height: 22px; border-radius: 1.5px;
  background: linear-gradient(to bottom, var(--primary), var(--accent-hot));
  opacity: 0.25;
  box-shadow: 0 0 8px rgba(67,56,202,0.12);
}
.connector-chip {
  font-size: 0.55rem;
  color: var(--muted);
  background: linear-gradient(135deg, rgba(67,56,202,0.04), rgba(234,88,12,0.04));
  padding: 0.1rem 0.45rem;
  border-radius: 0.75rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
body.dark .connector-chip {
  background: linear-gradient(135deg, rgba(67,56,202,0.1), rgba(234,88,12,0.1));
  color: #a8a29e;
}
.connector-chip .conn-icon { font-size: 0.6rem; }

.day-notes-card {
  background: linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%);
  border-radius: var(--radius);
  padding: 1rem;
  margin-bottom: 0.75rem;
}
body.dark .day-notes-card { background: linear-gradient(135deg, #44403C 0%, #57534E 100%); }
.day-notes-label { font-family: var(--font-display); font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--accent-warm); margin-bottom: 0.5rem; }
body.dark .day-notes-label { color: #FCD34D; }
.day-notes-text { font-size: 0.85rem; line-height: 1.5; color: var(--text); white-space: pre-line; }
body.dark .day-notes-text { color: var(--text-dark); }

.duration-badge {
  align-self: end;
  background: rgba(67,56,202,0.08);
  color: var(--primary);
  font-size: 0.7rem;
  font-weight: 600;
  padding: 0.25rem 0.6rem;
  border-radius: 2rem;
  white-space: nowrap;
}
body.dark .duration-badge { background: rgba(67,56,202,0.2); color: #a5b4fc; }

/* Dark mode toggle */
.theme-toggle {
  position: fixed;
  top: env(safe-area-inset-top, 0.75rem);
  right: 0.75rem;
  z-index: 300;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  font-size: 1.2rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  transition: background 300ms ease;
}
body.dark .theme-toggle { background: rgba(30,41,59,0.8); }

/* Footer */
.footer {
  text-align: center;
  padding: 2rem 1rem;
  font-size: 0.8rem;
  color: var(--muted);
}
body.dark .footer { color: #a8a29e; }
.footer .brand {
  background: linear-gradient(135deg, var(--primary), var(--accent-hot));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  font-weight: 700;
}

/* Empty state */
.empty-state {
  text-align: center;
  padding: 4rem 1rem;
}
.empty-state .emoji { font-size: 3rem; animation: float 3s ease-in-out infinite; }
.empty-state p { color: var(--muted); margin-top: 1rem; }

/* Animations */
@keyframes heroIn {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeSlideUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-10px); }
}
@keyframes carouselNudge {
  0%, 100% { transform: translateX(0); }
  50% { transform: translateX(-30px); }
}
.carousel-nudge {
  animation: carouselNudge 2s ease-in-out infinite;
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
"""


# ---------------------------------------------------------------------------
# JavaScript
# ---------------------------------------------------------------------------


def _js() -> str:
    """Return all JavaScript for the guide."""
    return """\
(function() {
  // Dark mode toggle
  var toggle = document.querySelector('.theme-toggle');
  var body = document.body;
  var stored = localStorage.getItem('wanderlog-theme');
  if (stored === 'dark' || (!stored && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    body.classList.add('dark');
  }
  toggle.addEventListener('click', function() {
    body.classList.toggle('dark');
    localStorage.setItem('wanderlog-theme', body.classList.contains('dark') ? 'dark' : 'light');
    toggle.textContent = body.classList.contains('dark') ? '\\u2600\\uFE0F' : '\\uD83C\\uDF19';
  });
  toggle.textContent = body.classList.contains('dark') ? '\\u2600\\uFE0F' : '\\uD83C\\uDF19';

  // Section tab switching
  var secTabs = document.querySelectorAll('.sec-tab');
  var secPanels = document.querySelectorAll('.sec-panel');
  var contentArea = document.querySelector('.content-area');
  var glowMap = { itinerary: 'glow-itin', hotels: 'glow-hotel', flights: 'glow-flight' };
  var activeMap = { itinerary: 'active-itin', hotels: 'active-hotel', flights: 'active-flight' };

  function switchSection(target) {
    secTabs.forEach(function(t) {
      t.classList.remove('active-itin', 'active-hotel', 'active-flight');
    });
    secPanels.forEach(function(p) { p.classList.remove('active'); });
    var targetTab = document.querySelector('.sec-tab[data-section="' + target + '"]');
    if (targetTab) targetTab.classList.add(activeMap[target]);
    var targetPanel = document.getElementById('sec-' + target);
    if (targetPanel) targetPanel.classList.add('active');
    if (contentArea) {
      contentArea.className = 'content-area ' + (glowMap[target] || '');
    }
  }

  secTabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      switchSection(tab.dataset.section);
    });
  });

  // Day carousel + pill navigation
  var pills = document.querySelectorAll('.tab-pill');
  var carousel = document.querySelector('.day-carousel');
  var tabBar = document.querySelector('.tab-bar');

  function scrollToActivePill(pill) {
    if (tabBar && pill) {
      pill.scrollIntoView({ behavior: 'smooth', inline: 'start', block: 'nearest' });
    }
  }

  function setActivePill(idx) {
    pills.forEach(function(p) { p.classList.remove('active'); });
    if (pills[idx]) {
      pills[idx].classList.add('active');
      scrollToActivePill(pills[idx]);
    }
  }

  function scrollCarouselTo(idx, smooth) {
    if (!carousel) return;
    var w = carousel.clientWidth;
    carousel.scrollTo({ left: idx * w, behavior: smooth ? 'smooth' : 'auto' });
  }

  // Pill click → scroll carousel
  pills.forEach(function(pill, i) {
    pill.addEventListener('click', function() {
      var idx = parseInt(pill.dataset.day, 10);
      setActivePill(idx);
      scrollCarouselTo(idx, true);
    });
  });

  // Carousel scroll → update active pill (live during swipe)
  var lastActiveIdx = -1;
  if (carousel) {
    carousel.addEventListener('scroll', function() {
      var w = carousel.clientWidth;
      if (w <= 0) return;
      var idx = Math.round(carousel.scrollLeft / w);
      if (idx !== lastActiveIdx) {
        lastActiveIdx = idx;
        setActivePill(idx);
      }
    }, { passive: true });
  }

  // Auto-detect today's date and select matching day
  var today = new Date().toISOString().slice(0, 10);
  var matchedIdx = -1;
  pills.forEach(function(pill, i) {
    if (pill.dataset.date === today) {
      matchedIdx = parseInt(pill.dataset.day, 10);
    }
  });
  if (matchedIdx >= 0) {
    setActivePill(matchedIdx);
    scrollCarouselTo(matchedIdx, false);
  } else {
    // No date match — Day 1, ensure scrolled to the left
    setActivePill(0);
    if (tabBar) tabBar.scrollLeft = 0;
    if (carousel) carousel.scrollLeft = 0;
  }

  // Scroll progress dots
  var scrollDots = document.querySelectorAll('.scroll-dot');
  if (tabBar && scrollDots.length) {
    tabBar.addEventListener('scroll', function() {
      var maxScroll = tabBar.scrollWidth - tabBar.clientWidth;
      if (maxScroll <= 0) return;
      var pct = tabBar.scrollLeft / maxScroll;
      var activeIdx = Math.round(pct * (scrollDots.length - 1));
      scrollDots.forEach(function(dot, i) {
        dot.classList.toggle('dot-active', i === activeIdx);
      });
    });
  }

  // PWA: inline service worker via Blob
  // Gentle nudge hint — animate carousel for up to 5s or until user interacts
  if (carousel && pills.length > 1) {
    carousel.classList.add('carousel-nudge');
    var stopNudge = function() {
      carousel.classList.remove('carousel-nudge');
      carousel.removeEventListener('scroll', stopNudge);
      carousel.removeEventListener('touchstart', stopNudge);
    };
    carousel.addEventListener('scroll', stopNudge, { passive: true });
    carousel.addEventListener('touchstart', stopNudge, { passive: true });
    setTimeout(stopNudge, 5000);
  }

  if ('serviceWorker' in navigator) {
    var swCode = "self.addEventListener('install', function(e) { e.waitUntil(caches.open('wanderlog-v1').then(function(c) { return c.add(location.href); })); self.skipWaiting(); });" +
      "self.addEventListener('fetch', function(e) { e.respondWith(caches.match(e.request).then(function(r) { return r || fetch(e.request); })); });";
    var blob = new Blob([swCode], {type: 'application/javascript'});
    navigator.serviceWorker.register(URL.createObjectURL(blob)).catch(function(){});
  }
})();
"""


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------


def _esc(text: str) -> str:
    """HTML-escape user text."""
    return html.escape(text, quote=True)


def _format_duration(minutes: int) -> str:
    """Format minutes as e.g. '2h 30m'."""
    if minutes <= 0:
        return ""
    h = minutes // 60
    m = minutes % 60
    if h and m:
        return f"{h}h {m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def _format_time_ampm(time_str: str) -> str:
    """Convert 24-hour time like '22:10' to '10:10 PM'. Returns original if unparseable."""
    if not time_str:
        return time_str
    try:
        parts = time_str.strip().split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        suffix = "AM" if hour < 12 else "PM"
        display_hour = hour % 12
        if display_hour == 0:
            display_hour = 12
        if minute:
            return f"{display_hour}:{minute:02d} {suffix}"
        return f"{display_hour} {suffix}"
    except (ValueError, IndexError):
        return time_str


def _maps_url(place: GuidePlace) -> str:
    """Build a Google Maps search URL."""
    if place.lat and place.lng:
        return f"https://www.google.com/maps/search/?api=1&query={place.lat},{place.lng}"
    if place.address:
        from urllib.parse import quote_plus
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(place.address)}"
    return ""


def _render_flights(guide: Guide) -> str:
    """Render flights as always-expanded boarding pass cards for the flights tab."""
    if not guide.flights:
        return (
            '<div class="empty-state">'
            '<div class="emoji">\U0001fae5</div>'
            '<p>No flights booked</p>'
            '</div>'
        )
    flight_count = len(guide.flights)
    flight_word = "flight" if flight_count == 1 else "flights"
    cards = []
    for f in guide.flights:
        # Header: route
        route = "Flight"
        if f.depart_airport and f.arrive_airport:
            route = f"{_esc(f.depart_airport)} \u2192 {_esc(f.arrive_airport)}"

        # Airline tag
        sub_parts = []
        if f.airline:
            sub_parts.append(f.airline)
        if f.flight_number:
            sub_parts.append(f.flight_number)
        airline_tag = _esc(" ".join(sub_parts)) if sub_parts else ""

        # Depart column
        depart_time = _format_time_ampm(f.depart_time) if f.depart_time else ""
        depart_date_label = ""
        if f.depart_date:
            try:
                dt = datetime.strptime(f.depart_date, "%Y-%m-%d")
                depart_date_label = dt.strftime("%a, %b %d")
            except ValueError:
                depart_date_label = _esc(f.depart_date)
        depart_airport_label = f"{_esc(f.depart_airport_name)} ({_esc(f.depart_airport)})" if f.depart_airport_name else ""

        # Arrive column
        arrive_time = _format_time_ampm(f.arrive_time) if f.arrive_time else ""
        arrive_date_label = ""
        if f.arrive_date:
            try:
                adt = datetime.strptime(f.arrive_date, "%Y-%m-%d")
                arrive_date_label = adt.strftime("%a, %b %d")
            except ValueError:
                arrive_date_label = _esc(f.arrive_date)
        arrive_airport_label = f"{_esc(f.arrive_airport_name)} ({_esc(f.arrive_airport)})" if f.arrive_airport_name else ""

        # Confirmation strip
        conf_parts = []
        if f.confirmation:
            conf_parts.append(f'Confirmation: <span class="bp-conf-code">{_esc(f.confirmation)}</span>')
        travelers_span = f"<span>{_esc(f.travelers)}</span>" if f.travelers else ""

        airline_html = f'<div class="bp-airline-tag">{airline_tag}</div>' if airline_tag else ""
        conf_strip = ""
        if conf_parts or travelers_span:
            left_conf = conf_parts[0] if conf_parts else ""
            conf_strip = f'<div class="bp-conf-strip"><span>{left_conf}</span>{travelers_span}</div>'

        cards.append(
            f'<div class="bp-card">'
            f'<div class="bp-header">'
            f'<div><div class="bp-route">{route}</div>{airline_html}</div>'
            f'</div>'
            f'<div class="bp-body">'
            f'<div class="bp-columns">'
            f'<div class="bp-col">'
            f'<div class="bp-label">Depart</div>'
            f'<div class="bp-val">{depart_time}</div>'
            f'<div class="bp-val-sub">{depart_date_label}</div>'
            f'<div class="bp-val-muted">{depart_airport_label}</div>'
            f'</div>'
            f'<div class="bp-col">'
            f'<div class="bp-label">Arrive</div>'
            f'<div class="bp-val">{arrive_time}</div>'
            f'<div class="bp-val-sub">{arrive_date_label}</div>'
            f'<div class="bp-val-muted">{arrive_airport_label}</div>'
            f'</div>'
            f'</div>'
            f'{conf_strip}'
            f'</div>'
            f'</div>'
        )
    return (
        f'<div class="sec-header">'
        f'<h2>\u2708\uFE0F Flights</h2>'
        f'<span class="sec-count cnt-flight">{flight_count} {flight_word}</span>'
        f'</div>'
        f'{"".join(cards)}'
    )


def _render_hotels(guide: Guide) -> str:
    """Render hotels as always-expanded boarding pass cards for the hotels tab."""
    if not guide.hotels:
        return (
            '<div class="empty-state">'
            '<div class="emoji">\U0001fae5</div>'
            '<p>No hotels booked</p>'
            '</div>'
        )
    hotel_count = len(guide.hotels)
    stay_word = "stay" if hotel_count == 1 else "stays"
    cards = []
    for h in guide.hotels:
        # Check-in / check-out date labels
        ci_label = ""
        co_label = ""
        if h.check_in:
            try:
                ci = datetime.strptime(h.check_in, "%Y-%m-%d")
                ci_label = ci.strftime("%a, %b %d")
            except ValueError:
                ci_label = _esc(h.check_in)
        if h.check_out:
            try:
                co = datetime.strptime(h.check_out, "%Y-%m-%d")
                co_label = co.strftime("%a, %b %d")
            except ValueError:
                co_label = _esc(h.check_out)

        # Nights tag
        nights_tag = ""
        if h.nights:
            night_word = "night" if h.nights == 1 else "nights"
            nights_tag = f"{h.nights} {night_word}"

        # Address as muted detail (consistent with flight airport line)
        addr_html = ""
        if h.address:
            addr_html = f'<div class="bp-val-muted">\U0001f4cd {_esc(h.address)}</div>'

        # Conf strip
        conf_parts = []
        if h.confirmation:
            conf_parts.append(f'Confirmation: <span class="bp-conf-code">{_esc(h.confirmation)}</span>')
        travelers_span = f"<span>{_esc(h.travelers)}</span>" if h.travelers else ""
        conf_strip = ""
        if conf_parts or travelers_span:
            left_conf = conf_parts[0] if conf_parts else ""
            conf_strip = f'<div class="bp-conf-strip"><span>{left_conf}</span>{travelers_span}</div>'

        nights_html = f'<div class="bp-airline-tag">{nights_tag}</div>' if nights_tag else ""

        cards.append(
            f'<div class="bp-card bp-hotel">'
            f'<div class="bp-header">'
            f'<div><div class="bp-route">{_esc(h.name)}</div>{nights_html}</div>'
            f'</div>'
            f'<div class="bp-body">'
            f'<div class="bp-columns">'
            f'<div class="bp-col">'
            f'<div class="bp-label">Check-in</div>'
            f'<div class="bp-val">{ci_label}</div>'
            f'{addr_html}'
            f'</div>'
            f'<div class="bp-col">'
            f'<div class="bp-label">Check-out</div>'
            f'<div class="bp-val">{co_label}</div>'
            f'</div>'
            f'</div>'
            f'{conf_strip}'
            f'</div>'
            f'</div>'
        )
    return (
        f'<div class="sec-header">'
        f'<h2>\U0001f3e8 Hotels</h2>'
        f'<span class="sec-count cnt-hotel">{hotel_count} {stay_word}</span>'
        f'</div>'
        f'{"".join(cards)}'
    )


def _render_connector(place: GuidePlace) -> str:
    """Render a connector between V6 place cards — single glow line + gradient chip."""
    travel_min = place.travel_minutes_to_next
    mode = place.travel_mode_to_next or ""
    mode_emoji = {
        "driving": "\U0001f697",    # 🚗
        "walking": "\U0001f6b6",    # 🚶
        "transit": "\U0001f68c",    # 🚌
        "bicycling": "\U0001f6b2",  # 🚲
    }.get(mode.lower(), "\U0001f4CD")  # 📍 default

    chip_inner = ""
    if travel_min > 0:
        if travel_min >= 60:
            h = travel_min // 60
            m = travel_min % 60
            t = f"{h}h {m}m" if m else f"{h}h"
        else:
            t = f"{travel_min} min"
        mode_label = mode.lower() if mode else ""
        chip_inner = f'<span class="conn-icon">{mode_emoji}</span> {t}'
        if mode_label:
            chip_inner += f' {mode_label}'
    else:
        chip_inner = "\u22EE"  # vertical ellipsis

    return (
        f'<div class="connector">'
        f'<div class="connector-line"></div>'
        f'<div class="connector-chip">{chip_inner}</div>'
        f'</div>'
    )


def _render_place_card(place: GuidePlace, idx: int) -> str:
    """Render a V6 Full Glow Connector place card."""
    delay = idx * 0.06
    cat_class = f"cat-{place.category}" if place.category else "cat-activity"
    emoji = _esc(place.icon) if place.icon else "\U0001f3f7\uFE0F"

    # Time — gradient text; show range if end_time exists
    time_html = ""
    if place.start_time and place.end_time:
        time_html = (
            f'<span class="place-time">'
            f'{_esc(place.start_time)}'
            f'<span class="t-sep"> \u2192 </span>'
            f'{_esc(place.end_time)}'
            f'</span>'
        )
    elif place.start_time:
        time_html = f'<span class="place-time">{_esc(place.start_time)}</span>'

    # Address
    address_html = ""
    if place.address:
        url = _maps_url(place)
        if url:
            address_html = f'<a class="address" href="{_esc(url)}" target="_blank" rel="noopener">\U0001f4CD {_esc(place.address)}</a>'
        else:
            address_html = f'<span class="address">\U0001f4CD {_esc(place.address)}</span>'

    notes_html = f'<div class="notes">{_esc(place.notes)}</div>' if place.notes else ""
    desc_html = f'<div class="place-desc">{_esc(place.description)}</div>' if place.description else ""

    # Tag pills — category (no emoji) + duration, with per-category styling
    tags = []
    if place.category:
        tag_class = f"tag-{place.category}" if place.category in ("food", "snack", "hotel") else ""
        tags.append(f'<span class="place-tag {tag_class}">{place.category.title()}</span>')
    dur = _format_duration(place.duration_minutes)
    if dur:
        # Explicit end_time → colored tag; estimated from Wanderlog → gray
        dur_class = "tag-dur-explicit" if place.end_time else "tag-dur"
        tags.append(f'<span class="place-tag {dur_class}">{dur}</span>')
    tags_html = f'<div class="place-tags">{"".join(tags)}</div>' if tags else ""

    return (
        f'<div class="place-card {cat_class}" style="animation-delay:{delay:.2f}s">'
        f'<div class="place-top">'
        f'<div class="place-badge">{emoji}</div>'
        f'<div class="place-body">'
        f'<div class="place-row"><h3>{_esc(place.name)}</h3>{time_html}</div>'
        f'{address_html}{notes_html}{desc_html}'
        f'</div>'
        f'</div>'
        f'{tags_html}'
        f'</div>'
    )


def _render_flight_card(flight: GuideFlight) -> str:
    """Render a flight card for the day view (always-expanded boarding pass)."""
    route = "Flight"
    if flight.depart_airport and flight.arrive_airport:
        route = f"{_esc(flight.depart_airport)} \u2192 {_esc(flight.arrive_airport)}"

    sub_parts = []
    if flight.airline:
        sub_parts.append(flight.airline)
    if flight.flight_number:
        sub_parts.append(flight.flight_number)
    airline_tag = _esc(" ".join(sub_parts)) if sub_parts else ""

    depart_time = _format_time_ampm(flight.depart_time) if flight.depart_time else ""
    depart_date_label = ""
    if flight.depart_date:
        try:
            dt = datetime.strptime(flight.depart_date, "%Y-%m-%d")
            depart_date_label = dt.strftime("%a, %b %d")
        except ValueError:
            depart_date_label = _esc(flight.depart_date)
    depart_airport_label = f"{_esc(flight.depart_airport_name)} ({_esc(flight.depart_airport)})" if flight.depart_airport_name else ""

    arrive_time = _format_time_ampm(flight.arrive_time) if flight.arrive_time else ""
    arrive_date_label = ""
    if flight.arrive_date:
        try:
            adt = datetime.strptime(flight.arrive_date, "%Y-%m-%d")
            arrive_date_label = adt.strftime("%a, %b %d")
        except ValueError:
            arrive_date_label = _esc(flight.arrive_date)
    arrive_airport_label = f"{_esc(flight.arrive_airport_name)} ({_esc(flight.arrive_airport)})" if flight.arrive_airport_name else ""

    conf_strip = ""
    conf_parts = []
    if flight.confirmation:
        conf_parts.append(f'Confirmation: <span class="bp-conf-code">{_esc(flight.confirmation)}</span>')
    travelers_span = f"<span>{_esc(flight.travelers)}</span>" if flight.travelers else ""
    if conf_parts or travelers_span:
        left_conf = conf_parts[0] if conf_parts else ""
        conf_strip = f'<div class="bp-conf-strip"><span>{left_conf}</span>{travelers_span}</div>'

    airline_html = f'<div class="bp-airline-tag">{airline_tag}</div>' if airline_tag else ""

    return (
        f'<div class="bp-card bp-day-card" style="margin-bottom:0.6rem;">'
        f'<div class="bp-header">'
        f'<div><div class="bp-route">{route}</div>{airline_html}</div>'
        f'</div>'
        f'<div class="bp-body">'
        f'<div class="bp-columns">'
        f'<div class="bp-col">'
        f'<div class="bp-label">Depart</div>'
        f'<div class="bp-val">{depart_time}</div>'
        f'<div class="bp-val-sub">{depart_date_label}</div>'
        f'<div class="bp-val-muted">{depart_airport_label}</div>'
        f'</div>'
        f'<div class="bp-col">'
        f'<div class="bp-label">Arrive</div>'
        f'<div class="bp-val">{arrive_time}</div>'
        f'<div class="bp-val-sub">{arrive_date_label}</div>'
        f'<div class="bp-val-muted">{arrive_airport_label}</div>'
        f'</div>'
        f'</div>'
        f'{conf_strip}'
        f'</div>'
        f'</div>'
    )


def _render_hotel_day_card(hotel: GuideHotel) -> str:
    """Render a hotel card for the day view (always-expanded boarding pass)."""
    ci_label = ""
    if hotel.check_in:
        try:
            ci = datetime.strptime(hotel.check_in, "%Y-%m-%d")
            ci_label = ci.strftime("%a, %b %d")
        except ValueError:
            ci_label = _esc(hotel.check_in)
    co_label = ""
    if hotel.check_out:
        try:
            co = datetime.strptime(hotel.check_out, "%Y-%m-%d")
            co_label = co.strftime("%a, %b %d")
        except ValueError:
            co_label = _esc(hotel.check_out)

    nights_tag = ""
    if hotel.nights:
        night_word = "night" if hotel.nights == 1 else "nights"
        nights_tag = f"{hotel.nights} {night_word}"

    addr_html = ""
    if hotel.address:
        addr_html = f'<div class="bp-val-muted">\U0001f4cd {_esc(hotel.address)}</div>'

    conf_strip = ""
    conf_parts = []
    if hotel.confirmation:
        conf_parts.append(f'Confirmation: <span class="bp-conf-code">{_esc(hotel.confirmation)}</span>')
    travelers_span = f"<span>{_esc(hotel.travelers)}</span>" if hotel.travelers else ""
    if conf_parts or travelers_span:
        left_conf = conf_parts[0] if conf_parts else ""
        conf_strip = f'<div class="bp-conf-strip"><span>{left_conf}</span>{travelers_span}</div>'

    nights_html = f'<div class="bp-airline-tag">{nights_tag}</div>' if nights_tag else ""

    return (
        f'<div class="bp-card bp-hotel bp-day-card" style="margin-bottom:0.6rem;">'
        f'<div class="bp-header">'
        f'<div><div class="bp-route">{_esc(hotel.name)}</div>{nights_html}</div>'
        f'</div>'
        f'<div class="bp-body">'
        f'<div class="bp-columns">'
        f'<div class="bp-col">'
        f'<div class="bp-label">Check-in</div>'
        f'<div class="bp-val">{ci_label}</div>'
        f'{addr_html}'
        f'</div>'
        f'<div class="bp-col">'
        f'<div class="bp-label">Check-out</div>'
        f'<div class="bp-val">{co_label}</div>'
        f'</div>'
        f'</div>'
        f'{conf_strip}'
        f'</div>'
        f'</div>'
    )


def _render_day(day: GuideDay, day_idx: int, total_days: int,
                flights: list[GuideFlight] | None = None,
                hotels: list[GuideHotel] | None = None) -> str:
    """Render a single day panel."""
    parts = []

    # Flight cards for this day (matching depart or arrive date)
    if flights:
        for f in flights:
            if f.depart_date == day.date or f.arrive_date == day.date:
                parts.append(_render_flight_card(f))

    # Hotel check-in cards for this day
    if hotels:
        for h in hotels:
            if h.check_in == day.date:
                parts.append(_render_hotel_day_card(h))

    # Day notes card
    if day.notes:
        parts.append(
            f'<div class="day-notes-card">'
            f'<div class="day-notes-label">Notes</div>'
            f'<div class="day-notes-text">{_esc(day.notes)}</div>'
            f'</div>'
        )
    # Place cards with connectors between them
    place_parts = []
    for i, p in enumerate(day.places):
        place_parts.append(_render_place_card(p, i))
        if i < len(day.places) - 1:
            place_parts.append(_render_connector(p))
    if place_parts:
        parts.append("".join(place_parts))
    if not parts:
        parts.append('<div class="empty-state"><div class="emoji">\U0001fae5</div><p>No events added for this date.</p></div>')
    return f'<div class="day-panel" data-day="{day_idx}">{"".join(parts)}</div>'


def _render_section_tabs(guide: Guide) -> str:
    """Render the top-level section tab bar (Itinerary / Hotels / Flights)."""
    return (
        '<div class="sec-tabs">'
        '<button class="sec-tab active-itin" data-section="itinerary">\U0001f4cd Itinerary</button>'
        '<button class="sec-tab" data-section="hotels">\U0001f3e8 Hotels</button>'
        '<button class="sec-tab" data-section="flights">\u2708\uFE0F Flights</button>'
        '</div>'
    )


def _render_tabs(guide: Guide) -> str:
    """Render the day tab bar."""
    if not guide.days:
        return ""
    pills = []
    for i, day in enumerate(guide.days):
        active = " active" if i == 0 else ""
        # Format date nicely
        try:
            dt = datetime.strptime(day.date, "%Y-%m-%d")
            date_label = dt.strftime("%a, %b %d")
        except (ValueError, TypeError):
            date_label = day.date
        date_iso = _esc(day.date) if day.date else ""
        pills.append(
            f'<button class="tab-pill{active}" data-day="{i}" data-date="{date_iso}">'
            f'<span class="day-label">Day {i + 1}</span>'
            f'<span class="day-date">{_esc(date_label)}</span>'
            f'</button>'
        )
    centered_class = " centered" if len(guide.days) <= 5 else ""
    dots = ""
    if len(guide.days) > 5:
        dots = (
            '<div class="scroll-dots">'
            + ''.join(
                f'<div class="scroll-dot{" dot-active" if i == 0 else ""}"></div>'
                for i in range(5)
            )
            + '</div>'
        )
    return f'<div class="tab-bar{centered_class}">{"".join(pills)}</div>{dots}'


def _date_range(guide: Guide) -> str:
    """Get a formatted date range string."""
    if not guide.days:
        return ""
    dates = [d.date for d in guide.days if d.date]
    if not dates:
        return ""
    try:
        start = datetime.strptime(dates[0], "%Y-%m-%d").strftime("%b %d, %Y")
        end = datetime.strptime(dates[-1], "%Y-%m-%d").strftime("%b %d, %Y")
        if start == end:
            return start
        return f"{start} \u2013 {end}"
    except (ValueError, TypeError):
        return ""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_guide_html(guide: Guide) -> str:
    """Generate a self-contained HTML trip guide. Returns HTML string."""
    date_range = _date_range(guide)
    subtitle_parts = []
    if date_range:
        subtitle_parts.append(date_range)
    if guide.timezone:
        subtitle_parts.append(_esc(guide.timezone))
    subtitle = " &middot; ".join(subtitle_parts)

    # Manifest data URL
    import json
    import base64
    manifest = json.dumps({
        "name": guide.name,
        "short_name": guide.name[:12],
        "display": "standalone",
        "theme_color": "#4338CA",
        "background_color": "#FFFBF5",
        "start_url": ".",
        "icons": []
    })
    manifest_b64 = base64.b64encode(manifest.encode()).decode()
    manifest_url = f"data:application/json;base64,{manifest_b64}"

    # Build day panels for itinerary tab
    if guide.days:
        tabs_html = _render_tabs(guide)
        days_html = "".join(
            _render_day(day, i, len(guide.days), flights=guide.flights, hotels=guide.hotels)
            for i, day in enumerate(guide.days)
        )
        day_count = len(guide.days)
        day_word = "day" if day_count == 1 else "days"
        # Duration key footnote
        dur_key = (
            '<div class="duration-key">'
            '<span class="dk-pill dk-gray">25m</span> = estimated avg visit'
            ' &nbsp;\u00B7&nbsp; '
            '<span class="dk-pill dk-colored">50m</span> = exact scheduled time'
            '</div>'
        )
        itinerary_content = (
            f'<div class="sec-header">'
            f'<h2>\U0001f4cd Itinerary</h2>'
            f'<span class="sec-count cnt-itin">{day_count} {day_word}</span>'
            f'</div>'
            f'{tabs_html}'
            f'<div class="day-carousel">{days_html}</div>'
            f'{dur_key}'
        )
    else:
        itinerary_content = (
            '<div class="empty-state">'
            '<div class="emoji">\u2708\uFE0F</div>'
            '<p>No days planned yet. Add some places to get started!</p>'
            '</div>'
        )

    # Build section tabs and panels
    section_tabs = _render_section_tabs(guide)
    flights_content = _render_flights(guide)
    hotels_content = _render_hotels(guide)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#4338CA">
<title>{_esc(guide.name)}</title>
<link rel="manifest" href="{manifest_url}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700&family=Geist:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
{_css()}
</style>
</head>
<body>
<button class="theme-toggle" aria-label="Toggle dark mode">\U0001f319</button>
<div class="container">
  <header class="hero">
    <div class="micro-label">\u2708\uFE0F Trip Guide</div>
    <h1>{_esc(guide.name)}</h1>
    <div class="subtitle">{subtitle}</div>
  </header>
  {section_tabs}
  <div class="content-area glow-itin" id="content-area">
    <div class="sec-panel active" id="sec-itinerary">
      {itinerary_content}
    </div>
    <div class="sec-panel" id="sec-hotels">
      {hotels_content}
    </div>
    <div class="sec-panel" id="sec-flights">
      {flights_content}
    </div>
  </div>
  <footer class="footer">
    \u2728 Generated by <span class="brand">WanderlogPro</span>
  </footer>
</div>
<script>
{_js()}
</script>
</body>
</html>"""


def write_guide(guide: Guide, output_path: str) -> str:
    """Generate guide HTML and write to file. Returns the output path."""
    content = generate_guide_html(guide)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    return output_path
