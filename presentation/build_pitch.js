"use strict";
const pptxgen = require("pptxgenjs");

// ── Paleta ────────────────────────────────────────────────────────────────────
const C = {
  navy:    "1E3A5F",
  navyDk:  "132845",
  white:   "FFFFFF",
  red:     "DC2626",
  amber:   "D97706",
  green:   "16A34A",
  ice:     "E8F0F8",
  muted:   "94A3B8",
  dark:    "1E293B",
  card:    "F1F5F9",
  accent:  "3B82F6",
};

const makeShadow = () => ({ type: "outer", blur: 8, offset: 3, angle: 135, color: "000000", opacity: 0.12 });

function addSlideHeader(slide, title, subtitle) {
  // Left accent bar
  slide.addShape("rect", { x: 0.4, y: 0.22, w: 0.06, h: 0.52, fill: { color: C.accent }, line: { color: C.accent } });
  slide.addText(title, {
    x: 0.55, y: 0.18, w: 9, h: 0.42,
    fontSize: 26, bold: true, color: C.navy, fontFace: "Calibri", margin: 0,
  });
  if (subtitle) {
    slide.addText(subtitle, {
      x: 0.55, y: 0.60, w: 9, h: 0.28,
      fontSize: 13, color: C.muted, fontFace: "Calibri", margin: 0,
    });
  }
  // Divider line
  slide.addShape("line", { x: 0.4, y: 0.94, w: 9.2, h: 0, line: { color: C.ice, width: 1.5 } });
}

// ── Build ─────────────────────────────────────────────────────────────────────
const pres = new pptxgen();
pres.layout = "LAYOUT_16x9";
pres.author  = "FraudIA Claims Team";
pres.title   = "FraudIA Claims — Pitch hackIAthon 2026";

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 1 — PORTADA
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navyDk };

  // Decorative left panel
  s.addShape("rect", { x: 0, y: 0, w: 3.2, h: 5.625, fill: { color: C.navy }, line: { color: C.navy } });

  // Shield icon area (colored circle)
  s.addShape("ellipse", { x: 0.85, y: 0.7, w: 1.5, h: 1.5, fill: { color: C.accent }, line: { color: C.accent } });
  s.addText("🛡️", { x: 0.85, y: 0.7, w: 1.5, h: 1.5, fontSize: 40, align: "center", valign: "middle" });

  // Left panel labels
  s.addText("hackIAthon 2026", {
    x: 0.1, y: 2.5, w: 3.0, h: 0.35,
    fontSize: 11, color: C.muted, bold: false, align: "center", fontFace: "Calibri",
  });
  s.addText("Reto Aseguradora del Sur", {
    x: 0.1, y: 2.85, w: 3.0, h: 0.35,
    fontSize: 11, color: C.white, bold: true, align: "center", fontFace: "Calibri",
  });
  s.addText("Sector Asegurador", {
    x: 0.1, y: 3.3, w: 3.0, h: 0.3,
    fontSize: 10, color: C.muted, align: "center", fontFace: "Calibri",
  });

  // Main title area
  s.addText("FraudIA", {
    x: 3.5, y: 1.0, w: 6.0, h: 0.95,
    fontSize: 62, bold: true, color: C.white, fontFace: "Calibri", margin: 0,
  });
  s.addText("Claims", {
    x: 3.5, y: 1.85, w: 6.0, h: 0.95,
    fontSize: 62, bold: true, color: C.accent, fontFace: "Calibri", margin: 0,
  });
  s.addText("Detector de Posibles Fraudes en Siniestros", {
    x: 3.5, y: 2.92, w: 6.1, h: 0.42,
    fontSize: 17, color: C.ice, fontFace: "Calibri", margin: 0,
  });

  // Divider
  s.addShape("line", { x: 3.5, y: 3.45, w: 5.8, h: 0, line: { color: C.accent, width: 2 } });

  // Tagline
  s.addText("Inteligencia Artificial al servicio del analista humano", {
    x: 3.5, y: 3.6, w: 6.1, h: 0.38,
    fontSize: 13, italic: true, color: C.muted, fontFace: "Calibri", margin: 0,
  });

  // Pills: tech stack
  const pills = ["Python", "Streamlit", "scikit-learn", "Claude API"];
  pills.forEach((p, i) => {
    const px = 3.5 + i * 1.52;
    s.addShape("rect", { x: px, y: 4.7, w: 1.38, h: 0.34, fill: { color: "1E3A5F" }, line: { color: C.accent, width: 1 }, rectRadius: 0.06 });
    s.addText(p, { x: px, y: 4.7, w: 1.38, h: 0.34, fontSize: 9, color: C.accent, align: "center", valign: "middle", fontFace: "Calibri" });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 2 — EL PROBLEMA
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "El Problema", "El analista enfrenta cientos de siniestros sin priorización inteligente");

  // 4 problem cards (2x2)
  const cards = [
    { icon: "👤", title: "Revisión manual", desc: "Dependiente de la experiencia individual del analista" },
    { icon: "🔀", title: "Reglas dispersas", desc: "Sin cruce automatizado de pólizas, proveedores y documentos" },
    { icon: "🕸️", title: "Patrones ocultos", desc: "Redes de asegurados y proveedores difíciles de detectar" },
    { icon: "📄", title: "Documentos alterados", desc: "Facturas y partes falsificados difíciles de detectar a escala" },
  ];

  const cols = [0.4, 5.1];
  const rows = [1.1, 3.1];
  cards.forEach((c, i) => {
    const cx = cols[i % 2];
    const cy = rows[Math.floor(i / 2)];
    s.addShape("rect", { x: cx, y: cy, w: 4.5, h: 1.75, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 }, shadow: makeShadow() });
    s.addText(c.icon, { x: cx + 0.15, y: cy + 0.25, w: 0.7, h: 0.7, fontSize: 26, align: "center", valign: "middle" });
    s.addText(c.title, { x: cx + 0.9, y: cy + 0.2, w: 3.4, h: 0.38, fontSize: 14, bold: true, color: C.navy, fontFace: "Calibri", margin: 0 });
    s.addText(c.desc,  { x: cx + 0.9, y: cy + 0.6, w: 3.4, h: 0.9,  fontSize: 12, color: C.dark, fontFace: "Calibri", wrap: true, margin: 0 });
  });

  // Bottom stat callout
  s.addShape("rect", { x: 0.4, y: 5.0, w: 9.2, h: 0.48, fill: { color: C.navy }, line: { color: C.navy } });
  s.addText("Solo el 1% de siniestros son ALTO riesgo — pero detectarlos a tiempo puede marcar la diferencia operativa y financiera", {
    x: 0.5, y: 5.0, w: 9.0, h: 0.48,
    fontSize: 12, color: C.white, align: "center", valign: "middle", italic: true, fontFace: "Calibri",
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 3 — LA SOLUCIÓN
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "FraudIA Claims — La Solución", "Bandeja inteligente de priorización antifraude");

  // 4 pillar cards
  const pillars = [
    { color: C.red,    icon: "🔴", num: "24", label: "Reglas antifraude", sub: "ponderadas con explicación" },
    { color: C.accent, icon: "🤖", num: "ML",  label: "RandomForest +",   sub: "IsolationForest" },
    { color: C.amber,  icon: "📝", num: "NLP", label: "TF-IDF similitud", sub: "narrativas de reclamos" },
    { color: C.green,  icon: "💬", num: "IA",  label: "Agente Claude",    sub: "consultas en lenguaje natural" },
  ];

  pillars.forEach((p, i) => {
    const cx = 0.35 + i * 2.35;
    // Card background
    s.addShape("rect", { x: cx, y: 1.05, w: 2.15, h: 2.9, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 }, shadow: makeShadow() });
    // Top accent bar
    s.addShape("rect", { x: cx, y: 1.05, w: 2.15, h: 0.22, fill: { color: p.color }, line: { color: p.color } });
    // Icon
    s.addText(p.icon, { x: cx, y: 1.28, w: 2.15, h: 0.65, fontSize: 28, align: "center", valign: "middle" });
    // Big number/label
    s.addText(p.num, { x: cx, y: 1.95, w: 2.15, h: 0.55, fontSize: 28, bold: true, color: p.color, align: "center", fontFace: "Calibri", margin: 0 });
    s.addText(p.label, { x: cx + 0.1, y: 2.52, w: 1.95, h: 0.35, fontSize: 11, bold: true, color: C.navy, align: "center", fontFace: "Calibri", margin: 0 });
    s.addText(p.sub,   { x: cx + 0.1, y: 2.87, w: 1.95, h: 0.65, fontSize: 10, color: C.muted, align: "center", wrap: true, fontFace: "Calibri", margin: 0 });
  });

  // Principle banner
  s.addShape("rect", { x: 0.35, y: 4.1, w: 9.3, h: 0.55, fill: { color: C.green }, line: { color: C.green } });
  s.addText("✅  PRINCIPIO CLAVE: NUNCA acusa fraude — genera alertas para revisión humana", {
    x: 0.4, y: 4.1, w: 9.2, h: 0.55,
    fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri",
  });

  // Hybrid score formula
  s.addText("Score híbrido = 40% Reglas + 25% Documental + 20% Modelo IA + 15% NLP", {
    x: 0.35, y: 4.82, w: 9.3, h: 0.35,
    fontSize: 11, color: C.muted, align: "center", italic: true, fontFace: "Calibri",
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 4 — ARQUITECTURA
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "Arquitectura Técnica", "Enfoque híbrido: Reglas + ML + NLP + Agente IA");

  // Flow diagram using shapes and arrows
  const flowItems = [
    { label: "Excel\n500 siniestros\n+ PDFs", x: 0.3, color: C.navy },
    { label: "Feature\nEngineering", x: 2.2, color: C.accent },
    { label: "Reglas + ML\n+ NLP + Red", x: 4.1, color: C.amber },
    { label: "Score\n0-100", x: 6.0, color: C.red },
    { label: "Dashboard\n+ Agente IA", x: 7.9, color: C.green },
  ];

  flowItems.forEach((item, i) => {
    const bx = item.x, by = 1.1, bw = 1.75, bh = 1.3;
    s.addShape("rect", { x: bx, y: by, w: bw, h: bh, fill: { color: item.color }, line: { color: item.color }, shadow: makeShadow() });
    s.addText(item.label, { x: bx, y: by, w: bw, h: bh, fontSize: 11, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri" });
    if (i < flowItems.length - 1) {
      s.addShape("line", { x: bx + bw, y: by + bh/2, w: 0.32, h: 0, line: { color: C.muted, width: 2 } });
      s.addText("▶", { x: bx + bw + 0.18, y: by + bh/2 - 0.13, w: 0.22, h: 0.26, fontSize: 9, color: C.muted, margin: 0 });
    }
  });

  // Stack section
  s.addText("STACK TECNOLÓGICO", {
    x: 0.4, y: 2.65, w: 9.2, h: 0.35,
    fontSize: 11, bold: true, color: C.muted, charSpacing: 3, fontFace: "Calibri",
  });

  const stackItems = [
    { tech: "Python 3.12", role: "Lenguaje base" },
    { tech: "Streamlit", role: "Dashboard web" },
    { tech: "scikit-learn", role: "ML / RF + IsoF" },
    { tech: "SHAP", role: "Explicabilidad" },
    { tech: "NetworkX", role: "Red relaciones" },
    { tech: "Claude API", role: "Agente IA" },
  ];

  stackItems.forEach((st, i) => {
    const sx = 0.3 + i * 1.6, sy = 3.1;
    s.addShape("rect", { x: sx, y: sy, w: 1.45, h: 0.85, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 } });
    s.addText(st.tech, { x: sx + 0.05, y: sy + 0.05, w: 1.35, h: 0.38, fontSize: 12, bold: true, color: C.navy, align: "center", fontFace: "Calibri", margin: 0 });
    s.addText(st.role, { x: sx + 0.05, y: sy + 0.44, w: 1.35, h: 0.32, fontSize: 9,  color: C.muted, align: "center", fontFace: "Calibri", margin: 0 });
  });

  // Architecture future note
  s.addShape("rect", { x: 0.3, y: 4.15, w: 9.4, h: 0.55, fill: { color: C.ice }, line: { color: "CBD5E1", width: 1 } });
  s.addText("Arquitectura futura escalable:  Oracle / PostgreSQL  →  FastAPI REST  →  Kubernetes  →  MLflow + Airflow", {
    x: 0.4, y: 4.15, w: 9.2, h: 0.55,
    fontSize: 11, color: C.navy, align: "center", valign: "middle", fontFace: "Calibri", italic: true,
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 5 — SCORE DE RIESGO
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "Score de Riesgo 0-100 — Semáforo", "Cada siniestro recibe un puntaje con explicación textual y código de regla");

  const levels = [
    { color: C.green, emoji: "🟢", range: "0 – 40", level: "VERDE / BAJO",   action: "Continuar flujo normal",                     n: "403 casos",  pct: "80.6%", bar: 8.06 },
    { color: C.amber, emoji: "🟡", range: "41 – 75", level: "AMARILLO / MEDIO", action: "Escalar a Unidad Antifraude — revisión doc.", n: "92 casos",   pct: "18.4%", bar: 1.84 },
    { color: C.red,   emoji: "🔴", range: "76 – 100", level: "ROJO / ALTO",   action: "Revisión especializada de campo",              n: "5 casos",    pct: "1.0%",  bar: 0.1 },
  ];

  levels.forEach((lv, i) => {
    const ry = 1.1 + i * 1.35;
    // Row card
    s.addShape("rect", { x: 0.3, y: ry, w: 9.4, h: 1.2, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 }, shadow: makeShadow() });
    // Color left accent
    s.addShape("rect", { x: 0.3, y: ry, w: 0.18, h: 1.2, fill: { color: lv.color }, line: { color: lv.color } });
    // Range badge
    s.addShape("rect", { x: 0.6, y: ry + 0.25, w: 1.1, h: 0.48, fill: { color: lv.color }, line: { color: lv.color } });
    s.addText(lv.range, { x: 0.6, y: ry + 0.25, w: 1.1, h: 0.48, fontSize: 16, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri" });
    // Level label
    s.addText(lv.level,  { x: 1.85, y: ry + 0.1,  w: 3.2, h: 0.42, fontSize: 14, bold: true, color: lv.color, fontFace: "Calibri", margin: 0 });
    s.addText(lv.action, { x: 1.85, y: ry + 0.55, w: 4.5, h: 0.38, fontSize: 11, color: C.dark, fontFace: "Calibri", margin: 0 });
    // Count + pct
    s.addText(lv.n,   { x: 6.6, y: ry + 0.1,  w: 1.4, h: 0.42, fontSize: 20, bold: true, color: lv.color, align: "right", fontFace: "Calibri", margin: 0 });
    s.addText(lv.pct, { x: 6.6, y: ry + 0.55, w: 1.4, h: 0.35, fontSize: 13, color: C.muted, align: "right", fontFace: "Calibri", margin: 0 });
    // Mini bar
    s.addShape("rect", { x: 8.1, y: ry + 0.3, w: Math.max(lv.bar * 0.14, 0.12), h: 0.55, fill: { color: lv.color }, line: { color: lv.color } });
  });

  // Score composition
  s.addText("COMPOSICIÓN DEL SCORE", {
    x: 0.3, y: 5.1, w: 9.4, h: 0.3,
    fontSize: 10, bold: true, color: C.muted, charSpacing: 2, fontFace: "Calibri",
  });
  const comps = [
    { label: "40%  Reglas", color: C.red },
    { label: "25%  Documental", color: C.amber },
    { label: "20%  Modelo IA", color: C.accent },
    { label: "15%  NLP", color: C.green },
  ];
  comps.forEach((c, i) => {
    const cx = 0.3 + i * 2.35;
    s.addShape("rect", { x: cx, y: 5.3, w: 0.12, h: 0.22, fill: { color: c.color }, line: { color: c.color } });
    s.addText(c.label, { x: cx + 0.18, y: 5.3, w: 2.0, h: 0.22, fontSize: 11, color: C.dark, fontFace: "Calibri", margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 6 — MODELO ML
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "Modelo ML — RandomForest + IsolationForest", "Entrenado y evaluado con datos sintéticos del reto");

  // 4 big metric boxes
  const metrics = [
    { label: "F1 Score",   value: "1.000", color: C.green },
    { label: "AUC-ROC",    value: "1.000", color: C.accent },
    { label: "Precision",  value: "1.000", color: C.amber },
    { label: "CV F1 mean", value: "0.951", color: C.navy },
  ];
  metrics.forEach((m, i) => {
    const mx = 0.3 + i * 2.38;
    s.addShape("rect", { x: mx, y: 1.05, w: 2.15, h: 1.55, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 }, shadow: makeShadow() });
    s.addShape("rect", { x: mx, y: 1.05, w: 2.15, h: 0.16, fill: { color: m.color }, line: { color: m.color } });
    s.addText(m.value, { x: mx, y: 1.22, w: 2.15, h: 0.8, fontSize: 38, bold: true, color: m.color, align: "center", fontFace: "Calibri", margin: 0 });
    s.addText(m.label, { x: mx, y: 2.05, w: 2.15, h: 0.38, fontSize: 12, color: C.dark, align: "center", fontFace: "Calibri", margin: 0 });
  });

  // Training info bar
  s.addShape("rect", { x: 0.3, y: 2.75, w: 9.4, h: 0.38, fill: { color: C.navy }, line: { color: C.navy } });
  s.addText("Entrenado: 400 siniestros   |   Evaluado: 100 siniestros   |   28 features   |   Validación cruzada 5-fold", {
    x: 0.3, y: 2.75, w: 9.4, h: 0.38,
    fontSize: 11, color: C.white, align: "center", valign: "middle", fontFace: "Calibri",
  });

  // Top SHAP features
  s.addText("TOP FEATURES (SHAP)", {
    x: 0.3, y: 3.3, w: 9.4, h: 0.3,
    fontSize: 10, bold: true, color: C.muted, charSpacing: 2, fontFace: "Calibri",
  });

  const features = [
    { name: "proveedor_lista_restrictiva", val: 0.091, color: C.red },
    { name: "similitud_narrativa",         val: 0.085, color: C.red },
    { name: "narrativa_clonada",           val: 0.065, color: C.amber },
    { name: "ratio_monto_suma",            val: 0.060, color: C.amber },
    { name: "dias_desde_inicio_poliza",    val: 0.054, color: C.accent },
  ];
  features.forEach((f, i) => {
    const fy = 3.7 + i * 0.34;
    const barW = f.val * 18;
    s.addText(f.name, { x: 0.3, y: fy, w: 4.2, h: 0.28, fontSize: 11, color: C.dark, fontFace: "Calibri", margin: 0 });
    s.addShape("rect", { x: 4.6, y: fy + 0.04, w: barW, h: 0.2, fill: { color: f.color }, line: { color: f.color } });
    s.addText((f.val * 100).toFixed(1) + "%", { x: 4.6 + barW + 0.1, y: fy, w: 0.6, h: 0.28, fontSize: 10, color: C.muted, fontFace: "Calibri", margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 7 — AGENTE IA
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "Agente IA — Consultas en Lenguaje Natural", "Powered by Claude API (Anthropic) — modo fallback programático disponible");

  // Left: questions the agent answers
  s.addText("EL AGENTE RESPONDE:", {
    x: 0.3, y: 1.05, w: 5.0, h: 0.3,
    fontSize: 10, bold: true, color: C.muted, charSpacing: 2, fontFace: "Calibri",
  });

  const questions = [
    "¿Cuáles son los 10 siniestros con mayor riesgo?",
    "¿Por qué este siniestro fue marcado ALTO?",
    "¿Qué proveedores concentran más alertas?",
    "¿Qué patrones repiten los reclamos sospechosos?",
    "Genera un resumen ejecutivo de casos críticos",
    "Recomienda qué casos revisar primero",
  ];
  questions.forEach((q, i) => {
    const qy = 1.4 + i * 0.48;
    s.addShape("rect", { x: 0.3, y: qy, w: 5.0, h: 0.38, fill: { color: C.ice }, line: { color: "CBD5E1", width: 1 } });
    s.addText("❓  " + q, { x: 0.4, y: qy, w: 4.8, h: 0.38, fontSize: 11, color: C.dark, valign: "middle", fontFace: "Calibri" });
  });

  // Right: report preview box
  s.addShape("rect", { x: 5.5, y: 1.05, w: 4.15, h: 4.3, fill: { color: C.navyDk }, line: { color: C.navy }, shadow: makeShadow() });
  s.addText("INFORME DE RIESGO\nANTIFRAUDE", {
    x: 5.6, y: 1.15, w: 3.95, h: 0.75,
    fontSize: 14, bold: true, color: C.white, align: "center", fontFace: "Calibri",
  });
  s.addShape("line", { x: 5.6, y: 1.95, w: 3.85, h: 0, line: { color: C.accent, width: 1 } });

  const reportLines = [
    { label: "Siniestro:", value: "SIN-0005" },
    { label: "Nivel:", value: "🔴 ALTO  (92/100)" },
    { label: "Reglas:", value: "R002, R006, R012, R019" },
    { label: "Acción:", value: "Revisión especializada" },
  ];
  reportLines.forEach((rl, i) => {
    const rly = 2.05 + i * 0.52;
    s.addText(rl.label, { x: 5.65, y: rly, w: 1.3, h: 0.38, fontSize: 10, color: C.muted, fontFace: "Calibri", margin: 0 });
    s.addText(rl.value, { x: 7.0,  y: rly, w: 2.5, h: 0.38, fontSize: 11, bold: true, color: C.white, fontFace: "Calibri", margin: 0 });
  });

  s.addShape("line", { x: 5.6, y: 4.18, w: 3.85, h: 0, line: { color: C.muted, width: 0.5 } });
  s.addText("Generado con Claude API (Anthropic)", {
    x: 5.6, y: 4.25, w: 3.95, h: 0.35,
    fontSize: 9, color: C.muted, align: "center", italic: true, fontFace: "Calibri",
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 8 — IMPACTO DE NEGOCIO
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navyDk };
  addSlideHeader(s, "Impacto de Negocio", "");
  // Override header colors for dark slide
  s.addShape("rect", { x: 0, y: 0, w: 10, h: 0.95, fill: { color: C.navyDk }, line: { color: C.navyDk } });
  s.addShape("rect", { x: 0.4, y: 0.22, w: 0.06, h: 0.52, fill: { color: C.accent }, line: { color: C.accent } });
  s.addText("Impacto de Negocio", { x: 0.55, y: 0.18, w: 9, h: 0.42, fontSize: 26, bold: true, color: C.white, fontFace: "Calibri", margin: 0 });
  s.addShape("line", { x: 0.4, y: 0.94, w: 9.2, h: 0, line: { color: "2D4A6F", width: 1.5 } });

  // Big stat at center top
  s.addText("De 500 casos a", { x: 1.5, y: 1.0, w: 3.5, h: 0.5, fontSize: 22, color: C.muted, align: "center", fontFace: "Calibri" });
  s.addText("5", { x: 4.0, y: 0.7, w: 2.0, h: 1.2, fontSize: 80, bold: true, color: C.red, align: "center", fontFace: "Calibri", margin: 0 });
  s.addText("prioritarios en segundos", { x: 5.0, y: 1.0, w: 3.5, h: 0.5, fontSize: 22, color: C.muted, align: "center", fontFace: "Calibri" });

  // 5 impact bullets
  const impacts = [
    { icon: "⏱️", text: "Revisión manual: de días → minutos" },
    { icon: "🎯", text: "5 casos ALTO + 92 MEDIO identificados automáticamente" },
    { icon: "📋", text: "Trazabilidad: cada alerta tiene código de regla y justificación textual" },
    { icon: "🚀", text: "Escalable a Oracle/PostgreSQL + Airflow + API REST" },
    { icon: "⚖️", text: "Ético: revisión humana obligatoria antes de cualquier decisión" },
  ];
  impacts.forEach((imp, i) => {
    const iy = 2.1 + i * 0.62;
    s.addText(imp.icon, { x: 0.4, y: iy, w: 0.55, h: 0.48, fontSize: 20, align: "center", valign: "middle" });
    s.addShape("rect", { x: 1.0, y: iy + 0.06, w: 8.6, h: 0.36, fill: { color: "1A304F" }, line: { color: "2D4A6F", width: 1 } });
    s.addText(imp.text, { x: 1.15, y: iy + 0.06, w: 8.4, h: 0.36, fontSize: 13, color: C.white, valign: "middle", fontFace: "Calibri" });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 9 — LIMITACIONES Y PRÓXIMOS PASOS
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  addSlideHeader(s, "Transparencia y Próximos Pasos", "Limitaciones conocidas y hoja de ruta de escalabilidad");

  // Left: Limitations
  s.addShape("rect", { x: 0.3, y: 1.05, w: 4.4, h: 0.4, fill: { color: C.amber }, line: { color: C.amber } });
  s.addText("⚠️  LIMITACIONES CONOCIDAS", { x: 0.3, y: 1.05, w: 4.4, h: 0.4, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri" });
  const limits = [
    "Datos sintéticos — requiere validación con datos reales de producción",
    "Modelo entrenado con etiqueta simulada (no supervisión real de fraude)",
    "Sin ingesta dinámica de documentos en tiempo real",
    "La similitud NLP puede generar falsos positivos en reclamos comunes",
  ];
  limits.forEach((l, i) => {
    const ly = 1.55 + i * 0.68;
    s.addShape("rect", { x: 0.3, y: ly, w: 4.4, h: 0.58, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 } });
    s.addText(l, { x: 0.45, y: ly + 0.05, w: 4.1, h: 0.48, fontSize: 11, color: C.dark, wrap: true, fontFace: "Calibri", margin: 0 });
  });

  // Right: Next steps
  s.addShape("rect", { x: 5.0, y: 1.05, w: 4.65, h: 0.4, fill: { color: C.accent }, line: { color: C.accent } });
  s.addText("🚀  PRÓXIMOS PASOS", { x: 5.0, y: 1.05, w: 4.65, h: 0.4, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri" });
  const nexts = [
    { step: "01", text: "Conectar al sistema core de siniestros vía API REST (Oracle / SAP)" },
    { step: "02", text: "OCR en tiempo real para documentos entrantes (Textract / Tesseract)" },
    { step: "03", text: "Reentrenamiento continuo con feedback del analista (MLflow)" },
    { step: "04", text: "Despliegue en Oracle Cloud / AWS con monitoreo Grafana" },
  ];
  nexts.forEach((n, i) => {
    const ny = 1.55 + i * 0.68;
    s.addShape("rect", { x: 5.0, y: ny, w: 4.65, h: 0.58, fill: { color: C.card }, line: { color: "E2E8F0", width: 1 } });
    s.addShape("rect", { x: 5.0, y: ny, w: 0.45, h: 0.58, fill: { color: C.accent }, line: { color: C.accent } });
    s.addText(n.step, { x: 5.0, y: ny, w: 0.45, h: 0.58, fontSize: 13, bold: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri" });
    s.addText(n.text, { x: 5.55, y: ny + 0.05, w: 4.0, h: 0.48, fontSize: 11, color: C.dark, wrap: true, fontFace: "Calibri", margin: 0 });
  });
}

// ══════════════════════════════════════════════════════════════════════════════
// SLIDE 10 — CIERRE / LISTO PARA CALIFICAR
// ══════════════════════════════════════════════════════════════════════════════
{
  const s = pres.addSlide();
  s.background = { color: C.navyDk };

  // Decorative right panel
  s.addShape("rect", { x: 6.9, y: 0, w: 3.1, h: 5.625, fill: { color: C.navy }, line: { color: C.navy } });
  s.addText("🛡️", { x: 7.2, y: 1.2, w: 2.5, h: 2.5, fontSize: 80, align: "center", valign: "middle" });

  // Main text
  s.addText("Listo para\nCalificar", {
    x: 0.4, y: 0.6, w: 6.2, h: 1.8,
    fontSize: 46, bold: true, color: C.white, fontFace: "Calibri", margin: 0,
  });
  s.addShape("line", { x: 0.4, y: 2.55, w: 5.8, h: 0, line: { color: C.accent, width: 2 } });

  // Checklist
  const items = [
    "Prototipo funcional — Dashboard Streamlit 7 páginas",
    "Código fuente modular — GitHub con estructura estándar",
    "Dataset sintético — 500 siniestros, 174 asegurados, 33 proveedores",
    "Documentación completa — arquitectura, modelo datos, reglas, IA",
    "Modelo ML entrenado — artefactos en /models",
  ];
  items.forEach((item, i) => {
    const iy = 2.75 + i * 0.42;
    s.addShape("rect", { x: 0.4, y: iy + 0.06, w: 0.3, h: 0.3, fill: { color: C.green }, line: { color: C.green } });
    s.addText("✓", { x: 0.4, y: iy + 0.06, w: 0.3, h: 0.3, fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle" });
    s.addText(item, { x: 0.82, y: iy, w: 5.8, h: 0.38, fontSize: 12, color: C.white, fontFace: "Calibri", valign: "middle", margin: 0 });
  });

  // Bottom tagline
  s.addShape("rect", { x: 0, y: 5.15, w: 6.85, h: 0.475, fill: { color: C.accent }, line: { color: C.accent } });
  s.addText("\"FraudIA Claims — Inteligencia Artificial que apoya al analista, sin reemplazarlo.\"", {
    x: 0.1, y: 5.15, w: 6.65, h: 0.475,
    fontSize: 11, italic: true, color: C.white, align: "center", valign: "middle", fontFace: "Calibri",
  });
}

// ── Write ─────────────────────────────────────────────────────────────────────
const OUT = "C:/Users/crist/OneDrive/Escritorio/Cris/Hackaton/hackiathon-aseguradora-del-sur/presentation/pitch_fraudia_claims.pptx";
pres.writeFile({ fileName: OUT })
  .then(() => console.log("✅  Guardado en:", OUT))
  .catch(e => { console.error("❌  Error:", e); process.exit(1); });
