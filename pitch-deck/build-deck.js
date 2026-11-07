const pptxgen = require('pptxgenjs');
const path = require('path');

const SHOT = (f) => path.join(__dirname, 'screenshots', f);

// JIMGAF brand palette (from frontend/public/styles/tokens.css)
const C = {
  brownDark: '2A1B12',
  brown: '4B2F21',
  brownMid: '6B4A34',
  taupe: '8A7A6E',
  cream: 'F7F2EC',
  sand: 'EFE8DF',
  sandLine: 'E4DACD',
  gold: 'C89B3C',
  goldTint: 'F6EDD9',
  goldHover: 'B98C2F',
  red: 'E1251B',
  green: '2E7D32',
  white: 'FFFFFF',
};

const FONT_HEAD = 'Cambria';
const FONT_BODY = 'Calibri';

const pres = new pptxgen();
pres.layout = 'LAYOUT_WIDE'; // 13.33 x 7.5 in
pres.author = 'JIMGAF Traceability';
pres.title = 'JIMGAF Traceability — Pitch Deck';

const PAGE_W = 13.333;
const PAGE_H = 7.5;

function footer(slide, label, pageNum) {
  slide.addText(label, {
    x: 0.5, y: 7.08, w: 8, h: 0.3, fontFace: FONT_BODY, fontSize: 10.5,
    color: C.taupe, align: 'left',
  });
  slide.addText(String(pageNum), {
    x: PAGE_W - 1.0, y: 7.08, w: 0.5, h: 0.3, fontFace: FONT_BODY, fontSize: 10.5,
    color: C.taupe, align: 'right',
  });
}

function screenshotCard(slide, file, x, y, w, h, { shadow = true } = {}) {
  // frame
  slide.addShape('roundRect', {
    x: x - 0.1, y: y - 0.1, w: w + 0.2, h: h + 0.2,
    rectRadius: 0.1, fill: { color: C.white },
    line: { color: C.sandLine, width: 1 },
    shadow: shadow ? { type: 'outer', color: '1A0F09', opacity: 0.35, blur: 18, offset: 6, angle: 90 } : undefined,
  });
  slide.addImage({
    path: file, x, y, w, h,
    sizing: { type: 'crop', w, h },
  });
}

// ---------------------------------------------------------------
// Slide 1 — Title
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.brownDark };

  // subtle accent arc
  s.addShape('ellipse', {
    x: 9.6, y: -2.6, w: 7, h: 7, fill: { color: C.brown, transparency: 40 }, line: { type: 'none' },
  });
  s.addShape('ellipse', {
    x: 10.6, y: 4.6, w: 5, h: 5, fill: { color: C.gold, transparency: 85 }, line: { type: 'none' },
  });

  s.addShape('roundRect', {
    x: 0.7, y: 0.6, w: 0.5, h: 0.5, rectRadius: 0.1, fill: { color: C.gold }, line: { type: 'none' },
  });
  s.addText('J', { x: 0.7, y: 0.6, w: 0.5, h: 0.5, fontFace: FONT_HEAD, bold: true, fontSize: 20, color: C.brownDark, align: 'center', valign: 'middle' });
  s.addText('JIMGAF', { x: 1.3, y: 0.58, w: 3, h: 0.3, fontFace: FONT_BODY, bold: true, fontSize: 14, color: C.cream, charSpacing: 1 });
  s.addText('TRACEABILITY', { x: 1.3, y: 0.86, w: 3, h: 0.25, fontFace: FONT_BODY, fontSize: 9.5, color: C.taupe, charSpacing: 2 });

  s.addText('COCOA TRACEABILITY FOR NIGERIAN LBAs', {
    x: 0.7, y: 2.55, w: 9, h: 0.4, fontFace: FONT_BODY, fontSize: 14, bold: true,
    color: C.gold, charSpacing: 2,
  });
  s.addText([
    { text: 'Every kilo, traced back to a ', options: { color: C.cream } },
    { text: 'registered farmer.', options: { color: C.gold, italic: true } },
  ], {
    x: 0.7, y: 2.95, w: 11.3, h: 1.9, fontFace: FONT_HEAD, fontSize: 54, bold: true,
    color: C.cream, lineSpacing: 60, valign: 'top',
  });
  s.addText(
    "A digital register that turns a broker lot's weight and receipt range into a quota-respecting farmer list — certified, receipted, and export-ready in seconds.",
    { x: 0.7, y: 4.75, w: 8.3, h: 0.9, fontFace: FONT_BODY, fontSize: 16, color: C.taupe, lineSpacing: 22 }
  );

  s.addShape('line', { x: 0.7, y: 5.85, w: 2.2, h: 0, line: { color: C.gold, width: 2 } });
  s.addText("PREPARED FOR LICENSED BUYING AGENTS  ·  2026", {
    x: 0.7, y: 6.0, w: 8, h: 0.3, fontFace: FONT_BODY, fontSize: 10.5, color: C.taupe, charSpacing: 1.5,
  });
}

// ---------------------------------------------------------------
// Slide 2 — The problem
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.cream };

  s.addText('THE PROBLEM', { x: 0.7, y: 0.55, w: 6, h: 0.35, fontFace: FONT_BODY, bold: true, fontSize: 13, color: C.gold, charSpacing: 2 });
  s.addText('Paper trails break exactly where buyers need proof', {
    x: 0.7, y: 0.92, w: 11.6, h: 0.9, fontFace: FONT_HEAD, bold: true, fontSize: 32, color: C.brownDark,
  });

  const problems = [
    ['No digital evidence', 'Certificates and lab results sit in folders and phones, not attached to the lots they belong to.'],
    ['Farmers get oversold', "Two pending lots can each claim a farmer's full remaining quota — nobody notices until it's too late."],
    ['Hours lost to Excel', 'Season-end reconciliation means rebuilding the farmer register by hand, lot by lot.'],
    ['No audit trail', "When a buyer asks \"who delivered this,\" the honest answer is often \"we're not sure.\""],
  ];
  const colW = 2.72, gap = 0.22, startX = 0.7, y0 = 2.15, cardH = 2.55;
  problems.forEach((p, i) => {
    const x = startX + i * (colW + gap);
    s.addShape('roundRect', {
      x, y: y0, w: colW, h: cardH, rectRadius: 0.08,
      fill: { color: C.white }, line: { color: C.sandLine, width: 1 },
    });
    s.addShape('roundRect', {
      x: x + 0.22, y: y0 + 0.28, w: 0.5, h: 0.5, rectRadius: 0.25,
      fill: { color: C.goldTint }, line: { type: 'none' },
    });
    s.addText(String(i + 1), { x: x + 0.22, y: y0 + 0.28, w: 0.5, h: 0.5, fontFace: FONT_HEAD, bold: true, fontSize: 18, color: C.gold, align: 'center', valign: 'middle' });
    s.addText(p[0], { x: x + 0.22, y: y0 + 0.98, w: colW - 0.44, h: 0.6, fontFace: FONT_BODY, bold: true, fontSize: 15.5, color: C.brownDark, lineSpacing: 18 });
    s.addText(p[1], { x: x + 0.22, y: y0 + 1.5, w: colW - 0.44, h: 0.95, fontFace: FONT_BODY, fontSize: 11, color: C.brownMid, lineSpacing: 14.5 });
  });

  // Stat callout bar
  s.addShape('roundRect', { x: 0.7, y: 5.0, w: 11.93, h: 1.45, rectRadius: 0.1, fill: { color: C.brownDark }, line: { type: 'none' } });
  s.addText('53 DAYS', { x: 1.0, y: 5.18, w: 2.6, h: 1.1, fontFace: FONT_HEAD, bold: true, fontSize: 40, color: C.gold, valign: 'middle' });
  s.addText(
    [{ text: 'until EUDR due-diligence rules take effect for cocoa ', options: { color: C.cream, bold: true } },
     { text: '(30 Dec 2026, large & medium operators)', options: { color: C.taupe } }],
    { x: 3.75, y: 5.18, w: 8.6, h: 1.1, fontFace: FONT_BODY, fontSize: 16, valign: 'middle', lineSpacing: 21 }
  );
  footer(s, 'JIMGAF Traceability', 2);
}

// ---------------------------------------------------------------
// Slide 3 — Solution mechanism (statement + flow)
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.brownDark };
  s.addText('THE SOLUTION', { x: 0.7, y: 0.6, w: 6, h: 0.35, fontFace: FONT_BODY, bold: true, fontSize: 13, color: C.gold, charSpacing: 2 });
  s.addText('One system. Every kilo accounted for.', {
    x: 0.7, y: 0.98, w: 11.6, h: 0.9, fontFace: FONT_HEAD, bold: true, fontSize: 34, color: C.cream,
  });
  s.addText(
    'JIMGAF sits between your weighbridge and your buyer: it turns raw delivery numbers into a certified, farmer-level record — automatically, and without ever letting a farmer be oversold.',
    { x: 0.7, y: 1.8, w: 10.8, h: 0.7, fontFace: FONT_BODY, fontSize: 15, color: C.taupe, lineSpacing: 20 }
  );

  const steps = [
    ['Upload', 'Your Excel farmer register — codes, names, potential volume.'],
    ['Record', "A lot's total weight and receipt range as it arrives."],
    ['Allocate', 'The system splits it across eligible farmers automatically — never past their potential.'],
    ['Certify', 'Reviewer accepts with a certification: Cocoa Horizons, Rainforest Alliance or EUDR.'],
    ['Export', '4-copy receipts, delivery slips and yield reports — ready for any buyer audit.'],
  ];
  const n = steps.length;
  const totalW = 11.93, gap = 0.28, boxW = (totalW - gap * (n - 1)) / n, y0 = 3.05, boxH = 2.9;
  steps.forEach((st, i) => {
    const x = 0.7 + i * (boxW + gap);
    s.addShape('roundRect', { x, y: y0, w: boxW, h: boxH, rectRadius: 0.08, fill: { color: C.brown }, line: { color: C.brownMid, width: 1 } });
    s.addShape('ellipse', { x: x + boxW / 2 - 0.26, y: y0 + 0.28, w: 0.52, h: 0.52, fill: { color: C.gold }, line: { type: 'none' } });
    s.addText(String(i + 1), { x: x + boxW / 2 - 0.26, y: y0 + 0.28, w: 0.52, h: 0.52, fontFace: FONT_HEAD, bold: true, fontSize: 18, color: C.brownDark, align: 'center', valign: 'middle' });
    s.addText(st[0], { x: x + 0.15, y: y0 + 1.0, w: boxW - 0.3, h: 0.4, fontFace: FONT_BODY, bold: true, fontSize: 15, color: C.gold, align: 'center' });
    s.addText(st[1], { x: x + 0.18, y: y0 + 1.42, w: boxW - 0.36, h: 1.35, fontFace: FONT_BODY, fontSize: 10.5, color: C.cream, align: 'center', lineSpacing: 13.5 });
    if (i < n - 1) {
      s.addShape('line', {
        x: x + boxW + 0.02, y: y0 + boxH / 2, w: gap - 0.04, h: 0,
        line: { color: C.gold, width: 1.5, endArrowType: 'triangle' },
      });
    }
  });
  footer(s, 'JIMGAF Traceability', 3);
}

// ---------------------------------------------------------------
// Slide 4 — Dashboard screenshot
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.sand };
  s.addText('OVERVIEW', { x: 0.7, y: 0.5, w: 5, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('Your whole season, on one screen', {
    x: 0.7, y: 0.85, w: 5.3, h: 1.4, fontFace: FONT_HEAD, bold: true, fontSize: 28, color: C.brownDark, lineSpacing: 32,
  });
  const bullets = [
    'Farmers on file, potential volume and delivered-to-date at a glance',
    'Pending lots flagged separately from accepted ones',
    'Farmers nearing their quota limit surfaced automatically',
    'Recent lot activity with live status — no spreadsheet needed',
  ];
  s.addText(bullets.map((b) => ({ text: b, options: { bullet: { code: '25CF', indent: 14 }, breakLine: true, paraSpaceAfter: 12 } })), {
    x: 0.7, y: 2.4, w: 5.3, h: 3.2, fontFace: FONT_BODY, fontSize: 13.5, color: C.brownMid, lineSpacing: 18,
  });
  screenshotCard(s, SHOT('02-dashboard.png'), 6.55, 1.0, 6.1, 5.9);
  footer(s, 'JIMGAF Traceability — Dashboard', 4);
}

// ---------------------------------------------------------------
// Slide 5 — New Lot + Farmers (two screenshots)
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  s.addText('RECORDING A DELIVERY', { x: 0.7, y: 0.5, w: 8, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('Record what you know. The system protects the rest.', {
    x: 0.7, y: 0.85, w: 11.6, h: 0.7, fontFace: FONT_HEAD, bold: true, fontSize: 27, color: C.brownDark,
  });
  s.addText(
    "Your team enters the lot date, total weight and receipt range — optionally naming preferred farmers. JIMGAF fills in the rest from the active register, and a farmer's quota bar makes overselling visible before it happens.",
    { x: 0.7, y: 1.55, w: 11.6, h: 0.55, fontFace: FONT_BODY, fontSize: 13.5, color: C.brownMid, lineSpacing: 17 }
  );
  screenshotCard(s, SHOT('04-new-lot.png'), 0.7, 2.3, 6.9, 4.35);
  screenshotCard(s, SHOT('03-farmers.png'), 7.95, 2.3, 4.7, 4.35);
  s.addText('New lot — preferred-farmer search', { x: 0.7, y: 6.78, w: 6.9, h: 0.3, fontFace: FONT_BODY, italic: true, fontSize: 10.5, color: C.taupe, align: 'center' });
  s.addText('Farmer register — live quota tracking', { x: 7.95, y: 6.78, w: 4.7, h: 0.3, fontFace: FONT_BODY, italic: true, fontSize: 10.5, color: C.taupe, align: 'center' });
}

// ---------------------------------------------------------------
// Slide 6 — Lot detail HERO (certification + receipts)
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.brownDark };
  s.addText('THE PROOF', { x: 0.7, y: 0.5, w: 6, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('One click: certified, receipted, provable.', {
    x: 0.7, y: 0.85, w: 11.6, h: 0.65, fontFace: FONT_HEAD, bold: true, fontSize: 28, color: C.cream,
  });
  screenshotCard(s, SHOT('11-lot-detail.png'), 0.7, 1.65, 7.6, 5.15);

  const points = [
    ['Certification required to accept', 'Cocoa Horizons, Rainforest Alliance or EUDR — chosen before a lot can be accepted, never defaulted.'],
    ['4-copy farmer receipts', 'One original and three duplicates, generated per lot the moment it is accepted.'],
    ['Full farmer-level breakdown', 'Every receipt number, bag count and kilo traced to a named, registered farmer.'],
  ];
  let y = 1.75;
  points.forEach((p) => {
    s.addShape('roundRect', { x: 8.55, y, w: 0.28, h: 0.28, rectRadius: 0.06, fill: { color: C.gold }, line: { type: 'none' } });
    s.addText(p[0], { x: 9.0, y: y - 0.08, w: 3.65, h: 0.5, fontFace: FONT_BODY, bold: true, fontSize: 14, color: C.gold });
    s.addText(p[1], { x: 9.0, y: y + 0.38, w: 3.65, h: 1.0, fontFace: FONT_BODY, fontSize: 11, color: C.taupe, lineSpacing: 14.5 });
    y += 1.75;
  });
  footer(s, 'JIMGAF Traceability — Lot record', 6);
}

// ---------------------------------------------------------------
// Slide 7 — Documents
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.sand };
  s.addText('EVIDENCE, IN ONE PLACE', { x: 0.7, y: 0.5, w: 7, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('Every certificate, audit-ready', {
    x: 0.7, y: 0.85, w: 5.3, h: 1.1, fontFace: FONT_HEAD, bold: true, fontSize: 28, color: C.brownDark, lineSpacing: 32,
  });
  const bullets = [
    'Upload any file type — PDF, image, Word, scanned certificate',
    'Supports Cocoa Horizons, Rainforest Alliance and EUDR evidence',
    'Attached to the LBA account, visible to your whole team',
    'One download away when a buyer requests proof',
  ];
  s.addText(bullets.map((b) => ({ text: b, options: { bullet: { code: '25CF', indent: 14 }, breakLine: true, paraSpaceAfter: 12 } })), {
    x: 0.7, y: 2.45, w: 5.3, h: 3.0, fontFace: FONT_BODY, fontSize: 13.5, color: C.brownMid, lineSpacing: 18,
  });
  screenshotCard(s, SHOT('06-documents.png'), 6.55, 1.0, 6.1, 5.9);
  footer(s, 'JIMGAF Traceability — Documents', 7);
}

// ---------------------------------------------------------------
// Slide 8 — Farmer detail (fairness / premium)
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  s.addText('FAIR TO FARMERS', { x: 0.7, y: 0.5, w: 7, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('Transparent payment, farmer by farmer', {
    x: 0.7, y: 0.85, w: 5.3, h: 1.1, fontFace: FONT_HEAD, bold: true, fontSize: 27, color: C.brownDark, lineSpacing: 31,
  });
  const bullets = [
    'Premium accrues automatically from delivered kilos',
    'Incentives and bonuses logged against the right farmer',
    'Full delivery history — every lot, date and volume',
    'Builds the trust that keeps farmers selling to you first',
  ];
  s.addText(bullets.map((b) => ({ text: b, options: { bullet: { code: '25CF', indent: 14 }, breakLine: true, paraSpaceAfter: 12 } })), {
    x: 0.7, y: 2.4, w: 5.3, h: 3.2, fontFace: FONT_BODY, fontSize: 13.5, color: C.brownMid, lineSpacing: 18,
  });
  screenshotCard(s, SHOT('12-farmer-detail.png'), 6.55, 1.0, 6.1, 5.9);
  footer(s, 'JIMGAF Traceability — Farmer profile', 8);
}

// ---------------------------------------------------------------
// Slide 9 — Why it matters for Nigerian cocoa (two columns)
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.brownDark };
  s.addText('THE BIGGER PICTURE', { x: 0.7, y: 0.55, w: 8, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('Why this matters beyond one LBA', {
    x: 0.7, y: 0.92, w: 11.6, h: 0.7, fontFace: FONT_HEAD, bold: true, fontSize: 30, color: C.cream,
  });

  const colW = 5.65, gap = 0.6, y0 = 2.0, h = 4.45;
  const cols = [
    ['For your business', C.gold, [
      'Close a season in hours, not weeks of manual reconciliation',
      'Catch an oversold farmer before it becomes a dispute',
      'Win and keep premium buyers who require digital proof',
      'One account per LBA — your data is never shared with another company',
    ]],
    ['For Nigerian cocoa', C.gold, [
      'EUDR-ready evidence ahead of the 30 Dec 2026 enforcement date',
      'Verifiable support for Cocoa Horizons & Rainforest Alliance claims',
      'A cleaner, farmer-level data trail across the national supply chain',
      'Smallholder farmers paid accurately and on provable terms',
    ]],
  ];
  cols.forEach((col, i) => {
    const x = 0.7 + i * (colW + gap);
    s.addShape('roundRect', { x, y: y0, w: colW, h, rectRadius: 0.08, fill: { color: C.brown }, line: { color: C.brownMid, width: 1 } });
    s.addText(col[0], { x: x + 0.35, y: y0 + 0.3, w: colW - 0.7, h: 0.5, fontFace: FONT_HEAD, bold: true, fontSize: 19, color: col[1] });
    s.addText(col[2].map((b) => ({ text: b, options: { bullet: { code: '25CF', indent: 14 }, breakLine: true, paraSpaceAfter: 16 } })), {
      x: x + 0.35, y: y0 + 1.0, w: colW - 0.7, h: h - 1.3, fontFace: FONT_BODY, fontSize: 13, color: C.cream, lineSpacing: 18,
    });
  });
  footer(s, 'JIMGAF Traceability', 9);
}

// ---------------------------------------------------------------
// Slide 10 — Private to your LBA
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.cream };
  s.addText('OWNERSHIP & TRUST', { x: 0.7, y: 0.6, w: 6, h: 0.32, fontFace: FONT_BODY, bold: true, fontSize: 12.5, color: C.gold, charSpacing: 2 });
  s.addText('Your data. Your infrastructure. Your name.', {
    x: 0.7, y: 1.0, w: 11.6, h: 0.75, fontFace: FONT_HEAD, bold: true, fontSize: 30, color: C.brownDark,
  });
  s.addText(
    'JIMGAF is deployed as a dedicated, single-tenant stack for your LBA — not a shared multi-company platform. No other account can ever see your farmer register, your lots or your certificates.',
    { x: 0.7, y: 1.85, w: 10.6, h: 0.8, fontFace: FONT_BODY, fontSize: 15, color: C.brownMid, lineSpacing: 20 }
  );

  const cards = [
    ['Dedicated cloud stack', 'Your own database and servers on secure cloud infrastructure — isolated from every other LBA.'],
    ['Role-based access', 'Admins, Traceability Officers and Sourcing Managers each see only what their role needs.'],
    ['Full audit trail', 'Every user action — lot created, lot accepted, team member added — logged with who and when.'],
  ];
  const colW = 3.75, gap = 0.3, y0 = 3.0, cardH = 3.5;
  cards.forEach((c, i) => {
    const x = 0.7 + i * (colW + gap);
    s.addShape('roundRect', { x, y: y0, w: colW, h: cardH, rectRadius: 0.08, fill: { color: C.white }, line: { color: C.sandLine, width: 1 } });
    s.addShape('roundRect', { x: x + 0.3, y: y0 + 0.32, w: 0.55, h: 0.55, rectRadius: 0.28, fill: { color: C.goldTint }, line: { type: 'none' } });
    s.addText('●', { x: x + 0.3, y: y0 + 0.32, w: 0.55, h: 0.55, fontFace: FONT_BODY, fontSize: 16, color: C.gold, align: 'center', valign: 'middle' });
    s.addText(c[0], { x: x + 0.3, y: y0 + 1.1, w: colW - 0.6, h: 0.55, fontFace: FONT_BODY, bold: true, fontSize: 15.5, color: C.brownDark, lineSpacing: 19 });
    s.addText(c[1], { x: x + 0.3, y: y0 + 1.7, w: colW - 0.6, h: 1.6, fontFace: FONT_BODY, fontSize: 11.5, color: C.brownMid, lineSpacing: 15.5 });
  });
  footer(s, 'JIMGAF Traceability', 10);
}

// ---------------------------------------------------------------
// Slide 11 — Closing / CTA
// ---------------------------------------------------------------
{
  const s = pres.addSlide();
  s.background = { color: C.brownDark };
  s.addShape('ellipse', { x: -2.5, y: 4.2, w: 7, h: 7, fill: { color: C.brown, transparency: 45 }, line: { type: 'none' } });
  s.addShape('ellipse', { x: 9.8, y: -2.2, w: 5.5, h: 5.5, fill: { color: C.gold, transparency: 86 }, line: { type: 'none' } });

  s.addText('LET’S GET YOUR SEASON EUDR-READY', { x: 0.9, y: 2.15, w: 11, h: 0.4, fontFace: FONT_BODY, bold: true, fontSize: 14, color: C.gold, charSpacing: 2 });
  s.addText('Traceability your buyers can verify.\nFarmers your records can prove.', {
    x: 0.9, y: 2.6, w: 11.2, h: 1.9, fontFace: FONT_HEAD, bold: true, fontSize: 40, color: C.cream, lineSpacing: 48,
  });
  s.addText(
    'Bring your Excel farmer register — JIMGAF handles allocation, certification and audit-ready evidence from day one.',
    { x: 0.9, y: 4.55, w: 9.5, h: 0.6, fontFace: FONT_BODY, fontSize: 15, color: C.taupe, lineSpacing: 20 }
  );

  s.addShape('line', { x: 0.9, y: 5.5, w: 2.2, h: 0, line: { color: C.gold, width: 2 } });
  s.addText('JIMGAF TRACEABILITY', { x: 0.9, y: 5.65, w: 6, h: 0.3, fontFace: FONT_BODY, bold: true, fontSize: 11, color: C.cream, charSpacing: 1.5 });
  s.addText('A product built for Licensed Buying Agents in Nigeria', { x: 0.9, y: 5.95, w: 8, h: 0.3, fontFace: FONT_BODY, fontSize: 11, color: C.taupe });
}

pres.writeFile({ fileName: path.join(__dirname, 'JIMGAF_Traceability_Pitch.pptx') }).then(() => {
  console.log('written');
});
