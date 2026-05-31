/**
 * welcome-card-layout-validation.jsx
 *
 * Purpose : Visual validation preview for all 6 Welcome Card layout types.
 * Use     : Run in a React sandbox (Vite / StackBlitz) before production implementation.
 * Naming  : All identifiers use final production naming — no version suffixes.
 *
 * Layout types  : panel | full_bleed | cinematic | split | banner | band
 * Design dirs   : A (Premium Hero) | B (Branded Academy) | C (Athlete Spotlight)
 * Canvas sources: card_constants.py CANVAS_SIZES — all pixel values are authoritative.
 *
 * Validation guide overlay (toggle "SHOW GUIDES"):
 *   Blue   — photo zone
 *   Green  — content panel / breathing zone
 *   Orange — tag zone
 *   Red    — skill zone
 *   Purple — photo column (split/banner/band)
 */

import { useState, useRef } from "react";

/* ─── FONTS ─────────────────────────────────────────────────────────────────── */
const FONTS = `
  @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow+Condensed:wght@400;600;700;800&family=Rajdhani:wght@500;600;700&display=swap');
  * { box-sizing: border-box; margin: 0; padding: 0; }
`;

/* ─── DESIGN DIRECTIONS ─────────────────────────────────────────────────────── */
const DIRS = {
  A: {
    label: "Premium Hero",
    accent: "#c8a84b", accentSolid: "#8b6914",
    panelBg: "rgba(5,10,22,0.97)",
    photoOverlay: "linear-gradient(to top,rgba(5,10,25,0.97) 0%,rgba(5,10,25,0.58) 46%,rgba(5,10,25,0.07) 100%)",
    tagPosBg: "rgba(59,130,246,0.18)", tagPosBorder: "rgba(59,130,246,0.5)", tagPosColor: "#60a5fa",
    skillIndicator: "top-border", mode: "gold",
  },
  B: {
    label: "Branded Academy",
    accent: "#3b82f6", accentSolid: "#1d4ed8",
    panelBg: "#060e1d",
    photoOverlay: "linear-gradient(to top,rgba(6,14,29,0.98) 0%,rgba(10,20,50,0.60) 44%,rgba(6,14,29,0.05) 100%)",
    tagPosBg: "#1d4ed8", tagPosBorder: "#1d4ed8", tagPosColor: "#fff",
    skillIndicator: "dot", mode: "blue",
  },
  C: {
    label: "Athlete Spotlight",
    accent: "#a78bfa", accentSolid: "#7c3aed",
    panelBg: "rgba(0,0,0,0.95)",
    photoOverlay: "linear-gradient(to top,rgba(0,0,0,0.97) 0%,rgba(0,0,0,0.44) 52%,rgba(0,0,0,0.01) 100%)",
    tagPosBg: "rgba(167,139,250,0.15)", tagPosBorder: "rgba(167,139,250,0.5)", tagPosColor: "#c4b5fd",
    skillIndicator: "dot", mode: "purple",
  },
};

/* ─── SKILL DATA ─────────────────────────────────────────────────────────────── */
const SKILL_COLORS = ["#3b82f6", "#eab308", "#22c55e", "#ef4444"];
const SKILL_LABELS  = ["OUTFIELD", "SET PIECES", "MENTAL", "PHYSICAL"];

/* ─── PANEL LAYOUT CONFIGS  (one per platform, from CANVAS_SIZES) ─────────────
   photo_pct = photoH / canvasH — the key composition ratio.
   All values validated against the v2 reference implementation.  ─────────── */
const PANEL_CFG = {
  instagram_square: {
    w:1080, h:1080, photoH:780,  panelH:300,
    photoPct:"72.2%", panelPct:"27.8%",
    padX:36,  headlineSz:118, subSz:21, hlGap:13,
    crestSz:52, crestFs:16, tagFs:13,
    /* ↓ Compact spacing fix: skillH 168→148 frees +20px breathing; scoreSz/nameSz
       scaled down to maintain proportion in 300px panel (Dir C name = ~88px, fits). */
    skillScoreSz:32, skillLabelSz:9.5, skillH:148, nameSz:42,
    scale:0.255,
  },
  instagram_portrait: {
    w:1080, h:1350, photoH:740,  panelH:610,
    photoPct:"54.8%", panelPct:"45.2%",
    padX:42,  headlineSz:128, subSz:22, hlGap:14,
    crestSz:52, crestFs:16, tagFs:17,
    skillScoreSz:36, skillLabelSz:10, skillH:168, nameSz:88,
    scale:0.230,
  },
  instagram_story: {
    w:1080, h:1920, photoH:1060, panelH:860,
    photoPct:"55.2%", panelPct:"44.8%",
    padX:56,  headlineSz:162, subSz:27, hlGap:17,
    crestSz:64, crestFs:19, tagFs:20,
    skillScoreSz:36, skillLabelSz:10, skillH:168, nameSz:148,
    scale:0.185,
  },
};

/* ─── GUIDE OVERLAY HELPERS ─────────────────────────────────────────────────── */
const G_PHOTO    = { bg:"rgba(0,100,255,0.12)",  border:"rgba(0,100,255,0.5)",  label:"PHOTO",    color:"rgba(60,140,255,1)"   };
const G_CONTENT  = { bg:"rgba(0,180,80,0.10)",   border:"rgba(0,180,80,0.5)",   label:"CONTENT",  color:"rgba(0,200,100,1)"    };
const G_BREATHE  = { bg:"rgba(255,220,0,0.08)",  border:"rgba(255,220,0,0.45)", label:"BREATHING",color:"rgba(240,210,0,1)"    };
const G_TAGS     = { bg:"rgba(255,140,0,0.10)",  border:"rgba(255,140,0,0.5)",  label:"TAGS",     color:"rgba(255,160,40,1)"   };
const G_SKILLS   = { bg:"rgba(220,50,50,0.10)",  border:"rgba(220,50,50,0.5)",  label:"SKILLS",   color:"rgba(255,80,80,1)"    };
const G_PHOTO_COL= { bg:"rgba(160,0,255,0.10)",  border:"rgba(160,0,255,0.5)",  label:"PHOTO COL",color:"rgba(180,80,255,1)"   };

function GuideZone({ top, left, right, bottom, width, height, g, label, extra="" }) {
  return (
    <div style={{
      position:"absolute", top, left, right, bottom, width, height,
      background:g.bg, border:`2px solid ${g.border}`,
      pointerEvents:"none", zIndex:20,
    }}>
      <div style={{
        position:"absolute", top:3, left:6,
        fontSize:10, fontWeight:700, color:g.color,
        fontFamily:"'Barlow Condensed',sans-serif", letterSpacing:"0.08em",
        textShadow:"0 1px 3px rgba(0,0,0,0.9)",
      }}>{label}{extra ? ` · ${extra}` : ""}</div>
    </div>
  );
}

/* ─── PRIMITIVES ─────────────────────────────────────────────────────────────── */
function Photo({ photo, overlay, tint = "#1e3060" }) {
  return (
    <div style={{ position:"absolute", inset:0, overflow:"hidden" }}>
      {photo
        ? <img src={photo} alt="" style={{ position:"absolute",inset:0,width:"100%",height:"100%",objectFit:"cover",objectPosition:"top center" }}/>
        /* Tint ellipse at 35% (not 22%) — face-zone anchor, gradient richer without photo */
        : <div style={{ position:"absolute",inset:0,background:`radial-gradient(ellipse at 50% 35%,${tint} 0%,#060d1a 100%)` }}/>
      }
      <div style={{ position:"absolute", inset:0, background:overlay }}/>
    </div>
  );
}

function Crest({ size = 52, fs = 16 }) {
  return (
    <div style={{
      width:size, height:size, borderRadius:"50%", flexShrink:0,
      background:"linear-gradient(135deg,#c8a84b,#8b6914)",
      display:"flex", alignItems:"center", justifyContent:"center",
      fontSize:fs, fontWeight:900, color:"#fff", fontFamily:"'Rajdhani'",
    }}>LFA</div>
  );
}

function Tags({ dir, fs = 15, gap = 8 }) {
  const tp = `${Math.round(fs * 0.30)}px ${Math.round(fs * 0.60)}px`;
  return (
    <div style={{ display:"flex", gap, flexWrap:"wrap" }}>
      {["CENTRE FORWARD","HUNGARY","AMATEUR"].map((tag, i) => (
        <div key={tag} style={{
          padding:tp, borderRadius:4,
          background:i===0 ? dir.tagPosBg : "rgba(255,255,255,0.07)",
          border:`1px solid ${i===0 ? dir.tagPosBorder : "rgba(255,255,255,0.13)"}`,
          color:i===0 ? dir.tagPosColor : "rgba(255,255,255,0.65)",
          fontSize:fs, fontWeight:700, letterSpacing:"0.10em", textTransform:"uppercase",
          fontFamily:"'Barlow Condensed'", whiteSpace:"nowrap",
        }}>{tag}</div>
      ))}
    </div>
  );
}

function Skills({ dir, scoreSz = 36, labelSz = 10, h = 168, grid = "repeat(4,1fr)" }) {
  return (
    <div style={{ display:"grid", gridTemplateColumns:grid, height:h }}>
      {SKILL_LABELS.map((lb, i) => (
        <div key={lb} style={{
          display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center",
          gap:3, padding:`${Math.round(scoreSz*0.28)}px ${Math.round(scoreSz*0.15)}px`,
          borderLeft:i>0 ? "1px solid rgba(255,255,255,0.06)" : "none",
          borderTop:dir.skillIndicator==="top-border" ? `2.5px solid ${SKILL_COLORS[i]}` : "none",
        }}>
          {dir.skillIndicator === "dot" && (
            <div style={{ width:Math.round(scoreSz*0.30), height:Math.round(scoreSz*0.30), borderRadius:2, background:SKILL_COLORS[i], marginBottom:2 }}/>
          )}
          <div style={{ fontSize:scoreSz, fontWeight:800, color:"#fff", lineHeight:1, fontFamily:"'Bebas Neue'" }}>60</div>
          <div style={{ fontSize:labelSz, letterSpacing:"0.10em", color:"rgba(255,255,255,0.38)", textTransform:"uppercase", fontFamily:"'Barlow Condensed'", textAlign:"center" }}>{lb}</div>
        </div>
      ))}
    </div>
  );
}

function Headline({ dir, titleSz = 100, subSz = 16, gap = 12, singleLine = false }) {
  const title = singleLine ? "LION FOOTBALL ACADEMY" : "LION\nFOOTBALL\nACADEMY";
  return (
    <div>
      {dir.mode === "gold" && <>
        <div style={{ width:Math.round(titleSz*0.42), height:2.5, background:dir.accent, marginBottom:Math.round(gap*0.7) }}/>
        <div style={{ fontSize:subSz, fontWeight:600, letterSpacing:"0.22em", color:dir.accent, textTransform:"uppercase", fontFamily:"'Barlow Condensed'", marginBottom:Math.round(gap*0.5) }}>Welcome to</div>
      </>}
      {dir.mode === "blue" && (
        <div style={{ display:"inline-block", background:dir.accentSolid, padding:`3px ${subSz}px`, marginBottom:Math.round(gap*0.8), borderRadius:4, fontSize:Math.round(subSz*0.68), fontWeight:700, letterSpacing:"0.18em", color:"#fff", textTransform:"uppercase", fontFamily:"'Barlow Condensed'" }}>Welcome</div>
      )}
      {dir.mode === "purple" && (
        <div style={{ fontSize:Math.round(subSz*0.80), letterSpacing:"0.24em", fontWeight:600, color:"rgba(255,255,255,0.36)", textTransform:"uppercase", fontFamily:"'Barlow Condensed'", marginBottom:Math.round(gap*0.6) }}>Welcome to Lion Football Academy</div>
      )}
      <div style={{ fontFamily:"'Bebas Neue'", fontSize:titleSz, lineHeight:singleLine ? 1 : 0.88, color:"#fff", letterSpacing:"0.02em", textShadow:"0 4px 28px rgba(0,0,0,0.85)", whiteSpace:"pre-line" }}>
        {title}
      </div>
      {dir.mode === "blue" && (
        <div style={{ marginTop:Math.round(gap*0.6), height:1.5, background:`linear-gradient(90deg,${dir.accentSolid},rgba(29,78,216,0.15),transparent)` }}/>
      )}
    </div>
  );
}

/* ─── CONTENT PANEL (panel.html's structured bottom zone) ───────────────────── */
function ContentPanel({ dir, height, padX = 36, tagFs = 15, skillScoreSz = 36, skillLabelSz = 10, skillH = 168, nameSz = 52, guides = false }) {
  const tagPad = Math.round(tagFs * 0.9);
  const tagZoneH = tagFs * 1.6 + tagPad * 2;

  return (
    <div style={{ height, display:"flex", flexDirection:"column", background:dir.panelBg, position:"relative", overflow:"hidden",
      borderTop:dir.mode==="gold" ? `1px solid ${dir.accent}33` : "1px solid rgba(255,255,255,0.07)" }}>

      {/* ── Validation guides ────────────────────────────────────────────────── */}
      {guides && <GuideZone top={0} left={0} right={0} bottom={skillH+tagZoneH} g={G_BREATHE} label="BREATHING" extra={`${height-skillH-tagZoneH}px`}/>}
      {guides && <GuideZone bottom={skillH} left={0} right={0} height={tagZoneH} g={G_TAGS} label="TAGS" extra={`${Math.round(tagZoneH)}px`}/>}
      {guides && <GuideZone bottom={0} left={0} right={0} height={skillH} g={G_SKILLS} label="SKILLS" extra={`${skillH}px`}/>}

      {/* ── Breathing zone ───────────────────────────────────────────────────── */}
      <div style={{ flex:1, display:"flex", flexDirection:"column", justifyContent:"flex-end", padding:`18px ${padX}px 18px` }}>

        {dir.mode === "gold" && (
          <div style={{ height:1, background:`linear-gradient(90deg,${dir.accent}44,transparent)`, marginBottom:14 }}/>
        )}
        {dir.mode === "blue" && (
          <div style={{ display:"inline-flex", alignItems:"center", gap:10, marginBottom:14 }}>
            <div style={{ width:Math.round(tagFs*1.6), height:Math.round(tagFs*1.6), borderRadius:"50%", background:`linear-gradient(135deg,${dir.accent}33,${dir.accentSolid}22)`, border:`1px solid ${dir.accent}44`, display:"flex", alignItems:"center", justifyContent:"center", fontSize:Math.round(tagFs*0.55), fontWeight:800, color:dir.accent, fontFamily:"'Rajdhani'" }}>LFA</div>
            <div style={{ fontSize:Math.round(tagFs*0.65), fontWeight:600, letterSpacing:"0.18em", color:"rgba(255,255,255,0.22)", textTransform:"uppercase", fontFamily:"'Barlow Condensed'" }}>Lion Football Academy</div>
          </div>
        )}
        {dir.mode === "purple" && (
          <div>
            <div style={{ height:1.5, background:`linear-gradient(90deg,${dir.accent},${dir.accent}22,transparent)`, marginBottom:Math.round(nameSz*0.22) }}/>
            <div style={{ fontFamily:"'Bebas Neue'", fontSize:nameSz, lineHeight:0.87, color:"#fff", letterSpacing:"0.01em", whiteSpace:"pre-line" }}>{"JOHN\nDOE"}</div>
            <div style={{ marginTop:Math.round(nameSz*0.14), fontSize:Math.round(nameSz*0.17), fontWeight:600, letterSpacing:"0.20em", color:dir.accent, textTransform:"uppercase", fontFamily:"'Barlow Condensed'" }}>Welcome to Lion Football Academy</div>
          </div>
        )}
      </div>

      {/* ── Tags ─────────────────────────────────────────────────────────────── */}
      <div style={{ padding:`${tagPad}px ${padX}px` }}>
        <Tags dir={dir} fs={tagFs} gap={Math.round(tagFs*0.55)}/>
      </div>

      {/* ── Skills ───────────────────────────────────────────────────────────── */}
      <div style={{ height:skillH, borderTop:"1px solid rgba(255,255,255,0.07)", flexShrink:0 }}>
        <Skills dir={dir} scoreSz={skillScoreSz} labelSz={skillLabelSz} h={skillH}/>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   LAYOUT COMPONENTS
   Each component maps 1-to-1 to a production template file.
   ═══════════════════════════════════════════════════════════════════════════════ */

/* ── panel.html — instagram_square · instagram_portrait · instagram_story ──── */
function PanelLayout({ dir, photo, platform, guides = false }) {
  const c = PANEL_CFG[platform];
  return (
    <div style={{ width:c.w, height:c.h, position:"relative", background:dir.panelBg, fontFamily:"'Barlow Condensed'", overflow:"hidden" }}>

      {/* Photo zone */}
      <div style={{ position:"absolute", top:0, left:0, right:0, height:c.photoH }}>
        <Photo photo={photo} overlay={dir.photoOverlay} tint="#1e3a6e"/>
        {!photo && (
          <div style={{ position:"absolute",top:"18%",left:0,right:0,textAlign:"center",
            fontFamily:"'Bebas Neue'",fontSize:Math.round(c.photoH * 0.38),lineHeight:1,
            color:"rgba(255,255,255,0.04)",letterSpacing:"0.10em",
            userSelect:"none",pointerEvents:"none" }}>JD</div>
        )}

        {/* Header */}
        <div style={{ position:"absolute",top:0,left:0,right:0,padding:`${Math.round(c.padX*0.75)}px ${c.padX}px`,display:"flex",alignItems:"center",justifyContent:"space-between",background:"linear-gradient(to bottom,rgba(0,0,0,0.52),transparent)" }}>
          <div style={{ display:"flex",alignItems:"center",gap:Math.round(c.crestSz*0.26) }}>
            <Crest size={c.crestSz} fs={c.crestFs}/>
            <div style={{ color:"rgba(255,255,255,0.5)",fontSize:Math.round(c.crestFs*1.0),letterSpacing:"0.15em",textTransform:"uppercase" }}>Lion Football Academy</div>
          </div>
          <div style={{ color:"rgba(255,255,255,0.72)",fontSize:Math.round(c.crestFs*1.38),fontWeight:600,letterSpacing:"0.12em" }}>JOHN DOE</div>
        </div>

        {/* Headline overlay */}
        <div style={{ position:"absolute",bottom:20,left:c.padX,right:c.padX }}>
          <Headline dir={dir} titleSz={c.headlineSz} subSz={c.subSz} gap={c.hlGap}/>
        </div>
      </div>

      {/* Content panel */}
      <div style={{ position:"absolute", top:c.photoH, left:0, right:0, bottom:0 }}>
        <ContentPanel dir={dir} height={c.panelH} padX={c.padX} tagFs={c.tagFs} skillScoreSz={c.skillScoreSz} skillLabelSz={c.skillLabelSz} skillH={c.skillH} nameSz={c.nameSz} guides={guides}/>
      </div>

      {/* Guide: photo zone */}
      {guides && <GuideZone top={0} left={0} right={0} height={c.photoH} g={G_PHOTO} label="PHOTO" extra={`${c.photoH}px = ${c.photoPct}`}/>}
      {guides && <GuideZone top={c.photoH} left={0} right={0} bottom={0} g={G_CONTENT} label="PANEL" extra={`${c.panelH}px = ${c.panelPct}`}/>}
    </div>
  );
}

/* ── full_bleed.html — facebook_square ────────────────────────────────────── */
function FullBleedLayout({ dir, photo, guides = false }) {
  const W = 1080, H = 1080;
  const PAD_X = 44;
  const SKILL_H = 100;
  return (
    <div style={{ width:W, height:H, position:"relative", fontFamily:"'Barlow Condensed'", overflow:"hidden" }}>
      <Photo photo={photo} tint="#152040"
        overlay="linear-gradient(to top,rgba(0,0,0,0.97) 0%,rgba(0,0,0,0.55) 40%,rgba(0,0,0,0.12) 75%,rgba(0,0,0,0.35) 100%)"/>

      {/* No-photo fallback: ghost initials centered (behind all overlaid content) */}
      {!photo && (
        <div style={{ position:"absolute",top:"22%",left:0,right:0,textAlign:"center",
          fontFamily:"'Bebas Neue'",fontSize:260,lineHeight:1,
          color:"rgba(255,255,255,0.04)",letterSpacing:"0.10em",
          userSelect:"none",pointerEvents:"none" }}>JD</div>
      )}

      {/* Top: minimal header — crest + player name only */}
      <div style={{ position:"absolute",top:0,left:0,right:0,padding:`30px ${PAD_X}px`,display:"flex",alignItems:"center",justifyContent:"space-between" }}>
        <Crest size={48} fs={15}/>
        <div style={{ color:"rgba(255,255,255,0.6)",fontSize:18,letterSpacing:"0.18em",fontWeight:600 }}>JOHN DOE</div>
      </div>

      {/* Bottom: player name hero + academy tagline + tags + skills */}
      <div style={{ position:"absolute",bottom:0,left:0,right:0,padding:`0 ${PAD_X}px 44px` }}>
        <div style={{ height:2,background:`linear-gradient(90deg,transparent,${dir.accent},transparent)`,marginBottom:28 }}/>
        <div style={{ fontFamily:"'Bebas Neue'",fontSize:96,lineHeight:0.86,color:"#fff",marginBottom:16,letterSpacing:"0.01em" }}>JOHN{"\n"}DOE</div>
        <div style={{ fontSize:18,fontWeight:600,letterSpacing:"0.20em",color:dir.accent,textTransform:"uppercase",marginBottom:22 }}>Welcome to Lion Football Academy</div>
        <Tags dir={dir} fs={17} gap={10}/>
        <div style={{ marginTop:28,borderTop:"1px solid rgba(255,255,255,0.08)",paddingTop:20,height:SKILL_H }}>
          <Skills dir={dir} scoreSz={38} labelSz={10} h={SKILL_H}/>
        </div>
      </div>

      {/* Guides */}
      {guides && <GuideZone top={0} left={0} right={0} height={H} g={G_PHOTO} label="FULL BLEED photo" extra="100%"/>}
    </div>
  );
}

/* ── cinematic.html — tiktok ─────────────────────────────────────────────── */
function CinematicLayout({ dir, photo, guides = false }) {
  const W = 1080, H = 1920;
  const PAD_X = 56;
  const NAME_SZ = 200;
  const SKILL_H = 120;
  /* Bottom content stack height estimate (for guide):
     56 bottom pad + 120 skills + 32 margin + ~40 tags + 18 margin + 42 tagline + 20 margin
     + NAME_SZ*0.82*2 ≈ 328px name = total ~656px */
  const CONTENT_STACK_H = 656;
  return (
    <div style={{ width:W, height:H, position:"relative", fontFamily:"'Barlow Condensed'", overflow:"hidden" }}>
      <Photo photo={photo} tint="#0d1f3c"
        /* Gradient: heavier shadow at top (0.35) anchors crest; lighter mid-zone (0.08) lets
           photo breathe; sharp fade from 30% keeps content stack legible. */
        overlay="linear-gradient(to top,rgba(0,0,0,0.97) 0%,rgba(0,0,0,0.72) 30%,rgba(0,0,0,0.08) 62%,rgba(0,0,0,0.35) 100%)"/>

      {/* No-photo fallback: ghost monogram anchored in face-zone (top 28-32% of canvas) */}
      {!photo && (
        <div style={{ position:"absolute",top:"18%",left:0,right:0,textAlign:"center",
          fontFamily:"'Bebas Neue'",fontSize:300,lineHeight:1,
          color:"rgba(255,255,255,0.045)",letterSpacing:"0.10em",
          userSelect:"none",pointerEvents:"none" }}>JD</div>
      )}

      {/* Top: crest only */}
      <div style={{ position:"absolute",top:0,left:0,right:0,padding:`52px ${PAD_X}px`,display:"flex",alignItems:"center",gap:16 }}>
        <Crest size={56} fs={16}/>
      </div>

      {/* Right: vertical brand accent bar */}
      <div style={{ position:"absolute",top:"30%",right:44,display:"flex",flexDirection:"column",alignItems:"center",gap:12 }}>
        <div style={{ width:1.5,height:80,background:`linear-gradient(to bottom,transparent,${dir.accent})` }}/>
        <div style={{ fontFamily:"'Barlow Condensed'",fontSize:14,fontWeight:700,letterSpacing:"0.24em",color:dir.accent,textTransform:"uppercase",writingMode:"vertical-rl",transform:"rotate(180deg)" }}>Lion Football Academy</div>
        <div style={{ width:1.5,height:80,background:`linear-gradient(to top,transparent,${dir.accent})` }}/>
      </div>

      {/* Bottom: player name + tagline + tags + glassmorphism skill container */}
      <div style={{ position:"absolute",bottom:0,left:0,right:0,padding:`0 ${PAD_X}px 56px` }}>
        <div style={{ fontFamily:"'Bebas Neue'",fontSize:NAME_SZ,lineHeight:0.82,color:"#fff",letterSpacing:"0.01em",textShadow:"0 8px 40px rgba(0,0,0,0.9)",whiteSpace:"pre-line" }}>{"JOHN\nDOE"}</div>
        <div style={{ fontSize:22,fontWeight:600,letterSpacing:"0.22em",color:dir.accent,textTransform:"uppercase",margin:"20px 0 18px" }}>Welcome to Lion Football Academy</div>
        <Tags dir={dir} fs={20} gap={12}/>
        <div style={{ marginTop:32,background:"rgba(255,255,255,0.06)",backdropFilter:"blur(16px)",borderRadius:16,border:"1px solid rgba(255,255,255,0.10)",overflow:"hidden",height:SKILL_H }}>
          <Skills dir={dir} scoreSz={26} labelSz={8} h={SKILL_H}/>
        </div>
      </div>

      {/* Guides */}
      {guides && <GuideZone top={0} left={0} right={0} height={H - CONTENT_STACK_H} g={G_PHOTO} label="PHOTO" extra={`~${H-CONTENT_STACK_H}px (${Math.round((H-CONTENT_STACK_H)/H*100)}%)`}/>}
      {guides && <GuideZone top={H - CONTENT_STACK_H} left={0} right={0} bottom={0} g={G_CONTENT} label="CONTENT STACK" extra={`~${CONTENT_STACK_H}px (${Math.round(CONTENT_STACK_H/H*100)}%)`}/>}
    </div>
  );
}

/* ── split.html — facebook_landscape  1200 × 630 ────────────────────────── */
function SplitLayout({ dir, photo, guides = false }) {
  const W = 1200, H = 630;
  const PHOTO_W = 480, PANEL_W = 720;
  const PAD_X   = 48;
  const HEADER_H = 72;
  // Headline height approx: 3 × 92 × 0.88 + pretitle ≈ 285px (Dir A/B) or ~260px (Dir C)
  const HL_H_APPROX = 290;
  const FLEX_PANEL_H = H - HEADER_H - HL_H_APPROX;  // ≈ 268px — should use flex:1 in CSS
  return (
    <div style={{ width:W, height:H, position:"relative", background:dir.panelBg, display:"flex", fontFamily:"'Barlow Condensed'", overflow:"hidden" }}>

      {/* Photo column */}
      <div style={{ width:PHOTO_W, height:H, position:"relative", flexShrink:0 }}>
        <Photo photo={photo} tint="#1a3060" overlay="linear-gradient(to right,rgba(0,0,0,0.04),rgba(5,10,22,0.94))"/>
        {!photo && (
          <div style={{ position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",
            fontFamily:"'Bebas Neue'",fontSize:120,color:"rgba(255,255,255,0.05)",
            letterSpacing:"0.10em",userSelect:"none",pointerEvents:"none" }}>JD</div>
        )}
        {guides && <GuideZone top={0} left={0} right={0} bottom={0} g={G_PHOTO_COL} label="PHOTO COL" extra={`${PHOTO_W}px = ${Math.round(PHOTO_W/W*100)}%`}/>}
      </div>

      {/* Content column */}
      <div style={{ width:PANEL_W, height:H, display:"flex", flexDirection:"column" }}>

        {/* Header bar */}
        <div style={{ height:HEADER_H, flexShrink:0, padding:`0 ${PAD_X}px`, display:"flex", alignItems:"center", justifyContent:"space-between", borderBottom:"1px solid rgba(255,255,255,0.06)" }}>
          <div style={{ display:"flex",alignItems:"center",gap:12 }}>
            <Crest size={38} fs={12}/>
            <div style={{ color:"rgba(255,255,255,0.42)",fontSize:13,letterSpacing:"0.15em",textTransform:"uppercase" }}>Lion Football Academy</div>
          </div>
          <div style={{ color:"rgba(255,255,255,0.58)",fontSize:16,fontWeight:600,letterSpacing:"0.10em" }}>JOHN DOE</div>
        </div>

        {/* Headline (fixed below header) */}
        <div style={{ padding:`22px ${PAD_X}px 0`, flexShrink:0 }}>
          <Headline dir={dir} titleSz={92} subSz={15} gap={11}/>
        </div>

        {/* ContentPanel fills remaining space — in CSS this is flex:1 */}
        <div style={{ flex:1, display:"flex", flexDirection:"column", minHeight:0 }}>
          <ContentPanel dir={dir} height={FLEX_PANEL_H} padX={PAD_X} tagFs={13} skillScoreSz={18} skillLabelSz={6.5} skillH={96} nameSz={38} guides={guides}/>
        </div>
      </div>

      {/* Guides */}
      {guides && <GuideZone top={0} left={PHOTO_W} right={0} height={HEADER_H} g={G_CONTENT} label="HEADER" extra={`${HEADER_H}px`}/>}
    </div>
  );
}

/* ── banner.html — banner_custom  1500 × 500 ─────────────────────────────
   Headline decision (validated): 2-line "LION FOOTBALL\nACADEMY" at 76px.
   Dir C: player name "JOHN DOE" as hero at 88px (single line, always safe);
          top intro text removed — avoids sandwich redundancy.
   Vertical dividers: 1.5px for more visible rhythm at 500px canvas height.
   ──────────────────────────────────────────────────────────────────────── */
function BannerLayout({ dir, photo, headlineVariant = "two-line", guides = false }) {
  const W = 1500, H = 500;
  const PHOTO_W  = 380;
  const SKILL_W  = 400;
  const CENTER_W = W - PHOTO_W - SKILL_W;  // 720px
  const PAD_X    = 60;

  // Dir C: always shows player name as hero (single-line, overflow-safe).
  // Dir A/B: two-line org name at 76px (validated safe) or single-line test variant.
  const hlText = dir.mode === "purple"
    ? "JOHN DOE"
    : (headlineVariant === "single-line" ? "LION FOOTBALL ACADEMY" : "LION FOOTBALL\nACADEMY");
  const hlSz   = dir.mode === "purple" ? 88
               : headlineVariant === "single-line" ? 86 : 76;

  return (
    <div style={{ width:W, height:H, position:"relative", background:dir.panelBg, display:"flex", fontFamily:"'Barlow Condensed'", overflow:"hidden" }}>

      {/* Photo strip */}
      <div style={{ width:PHOTO_W, height:H, position:"relative", flexShrink:0 }}>
        <Photo photo={photo} tint="#1a3060" overlay="linear-gradient(to right,rgba(0,0,0,0.04),rgba(5,10,22,0.95))"/>
        {!photo && (
          <div style={{ position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",
            fontFamily:"'Bebas Neue'",fontSize:100,color:"rgba(255,255,255,0.05)",
            letterSpacing:"0.10em",userSelect:"none",pointerEvents:"none" }}>JD</div>
        )}
        {guides && <GuideZone top={0} left={0} right={0} bottom={0} g={G_PHOTO_COL} label="PHOTO" extra={`${PHOTO_W}px = ${Math.round(PHOTO_W/W*100)}%`}/>}
      </div>

      {/* Vertical accent divider — 1.5px for rhythm clarity at 500px height */}
      <div style={{ width:1.5, background:`linear-gradient(to bottom,transparent,${dir.accent}66,transparent)`, flexShrink:0 }}/>

      {/* Center: welcome content */}
      <div style={{ width:CENTER_W, display:"flex", flexDirection:"column", padding:`36px ${PAD_X}px`, overflow:"hidden" }}>

        {/* Logo row */}
        <div style={{ display:"flex",alignItems:"center",gap:14,flexShrink:0,marginBottom:16 }}>
          <Crest size={44} fs={14}/>
          <div style={{ color:"rgba(255,255,255,0.42)",fontSize:14,letterSpacing:"0.16em",textTransform:"uppercase" }}>Lion Football Academy</div>
        </div>

        {/* Headline — vertically centered in remaining space */}
        <div style={{ flex:1, display:"flex", flexDirection:"column", justifyContent:"center" }}>
          {dir.mode === "gold"   && <div style={{ height:2.5, width:160, background:dir.accent, marginBottom:10 }}/>}
          {dir.mode === "blue"   && <div style={{ display:"inline-block",background:dir.accentSolid,padding:"3px 14px",borderRadius:4,marginBottom:10,fontSize:13,fontWeight:700,letterSpacing:"0.18em",color:"#fff",textTransform:"uppercase" }}>Welcome</div>}
          {/* Dir C: no top intro text — clean monolithic hero block */}
          <div style={{ fontFamily:"'Bebas Neue'",fontSize:hlSz,lineHeight:0.88,color:"#fff",letterSpacing:"0.02em",textShadow:"0 2px 16px rgba(0,0,0,0.7)",whiteSpace:"pre-line" }}>
            {hlText}
          </div>
          {dir.mode === "purple" && (
            <div style={{ marginTop:12,fontSize:13,fontWeight:600,letterSpacing:"0.22em",color:dir.accent,textTransform:"uppercase" }}>Welcome to Lion Football Academy</div>
          )}
          {dir.mode === "blue" && (
            <div style={{ marginTop:6,height:1.5,background:`linear-gradient(90deg,${dir.accentSolid},rgba(29,78,216,0.1),transparent)` }}/>
          )}
        </div>

        {/* Bottom: name + divider + tags (name omitted for Dir C — headline already shows it) */}
        <div style={{ display:"flex",alignItems:"center",gap:20,flexShrink:0 }}>
          {dir.mode !== "purple" && <>
            <div style={{ color:"rgba(255,255,255,0.55)",fontSize:17,fontWeight:600,letterSpacing:"0.10em",whiteSpace:"nowrap" }}>JOHN DOE</div>
            <div style={{ width:1,height:22,background:"rgba(255,255,255,0.14)",flexShrink:0 }}/>
          </>}
          <Tags dir={dir} fs={12} gap={7}/>
        </div>
      </div>

      {/* Vertical accent divider — 1.5px */}
      <div style={{ width:1.5, background:`linear-gradient(to bottom,transparent,${dir.accent}66,transparent)`, flexShrink:0 }}/>

      {/* Skills 2×2 — score 46px for comfort at 500px height */}
      <div style={{ width:SKILL_W, flexShrink:0, display:"grid", gridTemplateColumns:"repeat(2,1fr)" }}>
        {SKILL_LABELS.map((lb, i) => (
          <div key={lb} style={{ display:"flex",flexDirection:"column",alignItems:"center",justifyContent:"center",gap:6,borderLeft:i%2===1?"1px solid rgba(255,255,255,0.06)":"none",borderBottom:i<2?"1px solid rgba(255,255,255,0.06)":"none" }}>
            <div style={{ width:10,height:10,borderRadius:2,background:SKILL_COLORS[i] }}/>
            <div style={{ fontFamily:"'Bebas Neue'",fontSize:46,color:"#fff",lineHeight:1 }}>60</div>
            <div style={{ fontSize:10,color:"rgba(255,255,255,0.38)",letterSpacing:"0.10em",textTransform:"uppercase",fontFamily:"'Barlow Condensed'" }}>{lb}</div>
          </div>
        ))}
        {guides && <GuideZone top={0} left={0} right={0} bottom={0} g={G_SKILLS} label="SKILLS 2×2" extra={`${SKILL_W}px = ${Math.round(SKILL_W/W*100)}%`}/>}
      </div>
    </div>
  );
}

/* ── band.html — og  1200 × 630 ─────────────────────────────────────────── */
function BandLayout({ dir, photo, guides = false }) {
  const W = 1200, H = 630;
  /* STATS_W widened 200→220 for readability; OVERLAY_W adjusted to match (640+220=860 ≤ 1200). */
  const OVERLAY_W = 640;   // left content band (53.3% of canvas)
  const STATS_W   = 220;   // right stats strip (18.3%) — was 200, +20px for score/label comfort
  const PAD_X_OVL = 56;
  return (
    <div style={{ width:W, height:H, position:"relative", fontFamily:"'Barlow Condensed'", overflow:"hidden" }}>
      <Photo photo={photo} tint="#1a2e55"
        overlay="linear-gradient(to right,rgba(0,0,0,0.88) 0%,rgba(0,0,0,0.45) 55%,rgba(0,0,0,0.15) 100%)"/>

      {/* No-photo fallback: ghost field lines visible behind overlay band */}
      {!photo && (
        <div style={{ position:"absolute",top:"22%",left:OVERLAY_W+20,right:STATS_W+10,textAlign:"center",
          fontFamily:"'Bebas Neue'",fontSize:140,lineHeight:1,
          color:"rgba(255,255,255,0.035)",letterSpacing:"0.12em",
          userSelect:"none",pointerEvents:"none" }}>JD</div>
      )}

      {/* Left content overlay band */}
      <div style={{ position:"absolute",top:0,left:0,bottom:0,width:OVERLAY_W,padding:`42px ${PAD_X_OVL}px`,display:"flex",flexDirection:"column",justifyContent:"space-between" }}>

        {/* Top: logo row */}
        <div style={{ display:"flex",alignItems:"center",gap:12 }}>
          <Crest size={40} fs={12}/>
          <div style={{ color:"rgba(255,255,255,0.42)",fontSize:13,letterSpacing:"0.15em",textTransform:"uppercase" }}>Lion Football Academy</div>
        </div>

        {/* Mid: headline + tags */}
        <div>
          <Headline dir={dir} titleSz={96} subSz={16} gap={12}/>
          <div style={{ marginTop:20 }}>
            <Tags dir={dir} fs={14} gap={8}/>
          </div>
        </div>

        {/* Bottom: player name */}
        <div style={{ color:"rgba(255,255,255,0.55)",fontSize:17,fontWeight:600,letterSpacing:"0.10em" }}>JOHN DOE</div>
      </div>

      {/* Right stats strip — 220px, score 36px, label 10px, dot 10px, pad 18px */}
      <div style={{ position:"absolute",top:0,right:0,bottom:0,width:STATS_W,background:"rgba(0,0,0,0.58)",borderLeft:"1px solid rgba(255,255,255,0.07)",display:"flex",flexDirection:"column" }}>
        {SKILL_LABELS.map((lb, i) => (
          <div key={lb} style={{ flex:1,display:"flex",alignItems:"center",gap:12,padding:"0 18px",borderTop:i>0?"1px solid rgba(255,255,255,0.06)":"none" }}>
            <div style={{ width:10,height:10,borderRadius:2,background:SKILL_COLORS[i],flexShrink:0 }}/>
            <div>
              <div style={{ fontFamily:"'Bebas Neue'",fontSize:36,color:"#fff",lineHeight:1 }}>60</div>
              <div style={{ fontSize:10,letterSpacing:"0.08em",color:"rgba(255,255,255,0.38)",textTransform:"uppercase",fontFamily:"'Barlow Condensed'" }}>{lb}</div>
            </div>
          </div>
        ))}
        {guides && <GuideZone top={0} left={0} right={0} bottom={0} g={G_SKILLS} label="STATS STRIP" extra={`${STATS_W}px = ${Math.round(STATS_W/W*100)}%`}/>}
      </div>

      {/* Guides */}
      {guides && <GuideZone top={0} left={0} width={OVERLAY_W} bottom={0} g={G_CONTENT} label="OVERLAY BAND" extra={`${OVERLAY_W}px = ${Math.round(OVERLAY_W/W*100)}%`}/>}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════════
   SHELL COMPONENTS
   ═══════════════════════════════════════════════════════════════════════════════ */

function PreviewCard({ w, h, scale, label, sublabel, badge, warning, children }) {
  const BADGE_C = { panel:"#3b82f6", full_bleed:"#a78bfa", cinematic:"#f97316", split:"#22d3ee", banner:"#facc15", band:"#4ade80" };
  const bc = BADGE_C[badge] || "#fff";
  return (
    <div style={{ display:"flex",flexDirection:"column",alignItems:"center",gap:8 }}>
      <div style={{ display:"flex",alignItems:"center",gap:7,flexWrap:"wrap",justifyContent:"center" }}>
        <div style={{ padding:"2px 8px",borderRadius:4,background:bc+"22",border:`1px solid ${bc}55`,color:bc,fontSize:9,fontWeight:700,letterSpacing:"0.10em",textTransform:"uppercase",fontFamily:"'Barlow Condensed'" }}>{badge}</div>
        <div style={{ color:"rgba(255,255,255,0.8)",fontFamily:"'Barlow Condensed'",fontWeight:700,fontSize:13,letterSpacing:"0.06em" }}>{label}</div>
        {warning && <div style={{ padding:"2px 7px",borderRadius:4,background:"rgba(251,191,36,0.18)",border:"1px solid rgba(251,191,36,0.5)",color:"#fbbf24",fontSize:9,fontWeight:700,fontFamily:"'Barlow Condensed'" }}>⚠ {warning}</div>}
      </div>
      <div style={{ width:w*scale,height:h*scale,position:"relative",overflow:"hidden",borderRadius:8,boxShadow:"0 12px 40px rgba(0,0,0,0.7),0 0 0 1px rgba(255,255,255,0.07)" }}>
        <div style={{ width:w,height:h,transform:`scale(${scale})`,transformOrigin:"top left",position:"absolute",top:0,left:0 }}>{children}</div>
      </div>
      <div style={{ color:"rgba(255,255,255,0.28)",fontFamily:"'Barlow Condensed'",fontSize:10,letterSpacing:"0.06em" }}>{sublabel} · {w}×{h}</div>
    </div>
  );
}

function Section({ title, subtitle, children }) {
  return (
    <div style={{ marginBottom:52 }}>
      <div style={{ marginBottom:6 }}>
        <div style={{ fontFamily:"'Bebas Neue'",fontSize:20,color:"rgba(255,255,255,0.85)",letterSpacing:"0.12em" }}>{title}</div>
        <div style={{ fontSize:11,color:"rgba(255,255,255,0.32)",fontFamily:"'Barlow Condensed'",letterSpacing:"0.08em",marginTop:2 }}>{subtitle}</div>
      </div>
      <div style={{ height:1,background:"rgba(255,255,255,0.08)",marginBottom:24 }}/>
      <div style={{ display:"flex",gap:24,flexWrap:"wrap",justifyContent:"center" }}>{children}</div>
    </div>
  );
}

function Upload({ photo, onPhoto }) {
  const ref = useRef();
  const handle = f => { if (!f?.type.startsWith("image/")) return; const r = new FileReader(); r.onload = e => onPhoto(e.target.result); r.readAsDataURL(f); };
  return (
    <div onClick={() => ref.current.click()} style={{ border:"2px dashed rgba(255,255,255,0.15)",borderRadius:8,padding:"10px 18px",display:"flex",alignItems:"center",gap:12,cursor:"pointer",background:"rgba(255,255,255,0.02)" }}>
      <input ref={ref} type="file" accept="image/*" style={{ display:"none" }} onChange={e => handle(e.target.files[0])}/>
      {photo
        ? <img src={photo} alt="" style={{ width:40,height:40,borderRadius:6,objectFit:"cover" }}/>
        : <div style={{ width:40,height:40,borderRadius:6,background:"rgba(255,255,255,0.06)",display:"flex",alignItems:"center",justifyContent:"center",fontSize:16,color:"rgba(255,255,255,0.25)" }}>↑</div>
      }
      <div>
        <div style={{ color:photo?"#86efac":"rgba(255,255,255,0.75)",fontSize:12,fontWeight:600,fontFamily:"'Barlow Condensed'",letterSpacing:"0.04em" }}>{photo ? "Fotó betöltve · kattints a cseréhez" : "Játékosfotó feltöltése"}</div>
        <div style={{ color:"rgba(255,255,255,0.28)",fontSize:10,marginTop:2,fontFamily:"'Barlow Condensed'" }}>JPG · PNG</div>
      </div>
      {photo && <div onClick={e=>{e.stopPropagation();onPhoto(null);}} style={{ marginLeft:8,color:"rgba(255,255,255,0.3)",fontSize:16,cursor:"pointer" }}>✕</div>}
    </div>
  );
}

/* ─── APP ────────────────────────────────────────────────────────────────────── */
export default function App() {
  const [photo,     setPhoto]     = useState(null);
  const [dirKey,    setDirKey]    = useState("A");
  const [guides,    setGuides]    = useState(false);
  const [bannerVar, setBannerVar] = useState("two-line");

  const dir = DIRS[dirKey];

  return (
    <>
      <style>{FONTS}</style>
      <div style={{ minHeight:"100dvh",background:"radial-gradient(ellipse at 20% 30%,#0c1a2e 0%,#060810 70%)",padding:"clamp(16px,3vw,36px)",fontFamily:"'Barlow Condensed'" }}>
        <div style={{ maxWidth:1600,margin:"0 auto" }}>

          {/* ── Header ─────────────────────────────────────────────────────── */}
          <div style={{ marginBottom:24 }}>
            <div style={{ color:"rgba(255,255,255,0.28)",fontSize:10,letterSpacing:"0.20em",textTransform:"uppercase",marginBottom:5 }}>LFA · Welcome Card · Layout Validation</div>
            <h1 style={{ fontFamily:"'Bebas Neue'",fontSize:"clamp(24px,3.5vw,42px)",color:"#fff",letterSpacing:"0.04em",lineHeight:1 }}>
              6 Layout Types — Visual Validation
            </h1>
          </div>

          {/* ── Controls ────────────────────────────────────────────────────── */}
          <div style={{ display:"flex",gap:14,marginBottom:32,flexWrap:"wrap",alignItems:"center" }}>
            <Upload photo={photo} onPhoto={setPhoto}/>

            {/* Direction picker */}
            <div style={{ display:"flex",gap:6 }}>
              {Object.entries(DIRS).map(([k, d]) => (
                <button key={k} onClick={() => setDirKey(k)} style={{ padding:"7px 14px",borderRadius:6,cursor:"pointer",fontFamily:"'Barlow Condensed'",fontSize:12,fontWeight:700,letterSpacing:"0.10em",background:dirKey===k?d.accent+"22":"rgba(255,255,255,0.04)",border:`1.5px solid ${dirKey===k?d.accent:"rgba(255,255,255,0.12)"}`,color:dirKey===k?d.accent:"rgba(255,255,255,0.4)",transition:"all 0.15s" }}>
                  {k} · {d.label}
                </button>
              ))}
            </div>

            {/* Guide toggle */}
            <button onClick={() => setGuides(g => !g)} style={{ padding:"7px 14px",borderRadius:6,cursor:"pointer",fontFamily:"'Barlow Condensed'",fontSize:12,fontWeight:700,letterSpacing:"0.10em",background:guides?"rgba(255,220,0,0.12)":"rgba(255,255,255,0.04)",border:`1.5px solid ${guides?"rgba(255,220,0,0.5)":"rgba(255,255,255,0.12)"}`,color:guides?"#fde68a":"rgba(255,255,255,0.4)" }}>
              {guides ? "◉ GUIDES ON" : "◎ SHOW GUIDES"}
            </button>

            {/* Banner A/B headline: 2-line = confirmed production decision (validated safe).
                Toggle kept as a reference comparison only — not a design choice. */}
            <button onClick={() => setBannerVar(v => v === "two-line" ? "single-line" : "two-line")} style={{ padding:"7px 14px",borderRadius:6,cursor:"pointer",fontFamily:"'Barlow Condensed'",fontSize:12,fontWeight:700,letterSpacing:"0.10em",background:bannerVar==="two-line"?"rgba(134,239,172,0.10)":"rgba(251,191,36,0.08)",border:`1.5px solid ${bannerVar==="two-line"?"rgba(134,239,172,0.45)":"rgba(251,191,36,0.45)"}`,color:bannerVar==="two-line"?"#86efac":"#fbbf24" }}>
              BANNER A/B: {bannerVar === "two-line" ? "✓ 2-LINE (production)" : "⚠ 1-LINE (compare only)"}
            </button>
          </div>

          {/* ══ Section 1: PANEL ════════════════════════════════════════════ */}
          <Section title="PANEL" subtitle="panel.html — 3 platforms, same layout contract, platform_vars overrides only">
            {Object.entries(PANEL_CFG).map(([platform, c]) => (
              <PreviewCard key={platform} w={c.w} h={c.h} scale={c.scale} label={platform.replace("_"," ")} sublabel={`photo ${c.photoPct} · panel ${c.panelPct}`} badge="panel">
                <PanelLayout dir={dir} photo={photo} platform={platform} guides={guides}/>
              </PreviewCard>
            ))}
          </Section>

          {/* ══ Section 2: FULL BLEED + CINEMATIC ══════════════════════════ */}
          <Section title="FULL BLEED · CINEMATIC" subtitle="full_bleed.html + cinematic.html — player name as hero element (not organization name)">
            <PreviewCard w={1080} h={1080} scale={0.255} label="facebook_square" sublabel="player name hero · dual gradient" badge="full_bleed">
              <FullBleedLayout dir={dir} photo={photo} guides={guides}/>
            </PreviewCard>
            <PreviewCard w={1080} h={1920} scale={0.185} label="tiktok" sublabel="vertical accent bar · glassmorphism skills" badge="cinematic">
              <CinematicLayout dir={dir} photo={photo} guides={guides}/>
            </PreviewCard>
          </Section>

          {/* ══ Section 3: SPLIT · BANNER · BAND ════════════════════════════ */}
          <Section title="SPLIT · BANNER · BAND" subtitle="split.html + banner.html + band.html — horizontal formats requiring focused validation">
            <PreviewCard w={1200} h={630} scale={0.320} label="facebook_landscape" sublabel="2-col · header + headline + ContentPanel" badge="split">
              <SplitLayout dir={dir} photo={photo} guides={guides}/>
            </PreviewCard>
            <PreviewCard w={1500} h={500} scale={0.280} label="banner_custom" sublabel="3-col · 2×2 skills" badge="banner" warning={bannerVar === "single-line" ? "headline overflow" : undefined}>
              <BannerLayout dir={dir} photo={photo} headlineVariant={bannerVar} guides={guides}/>
            </PreviewCard>
            <PreviewCard w={1200} h={630} scale={0.320} label="og" sublabel="overlay band · 200px stats strip" badge="band">
              <BandLayout dir={dir} photo={photo} guides={guides}/>
            </PreviewCard>
          </Section>

          {/* ══ Validation notes ════════════════════════════════════════════ */}
          <div style={{ marginTop:16,padding:"18px 22px",background:"rgba(255,255,255,0.02)",border:"1px solid rgba(255,255,255,0.07)",borderRadius:10 }}>
            <div style={{ color:"rgba(255,255,255,0.55)",fontSize:11,fontFamily:"'Barlow Condensed'",letterSpacing:"0.06em",lineHeight:1.9 }}>
              <div style={{ color:"rgba(255,255,255,0.75)",fontWeight:700,marginBottom:6,fontSize:12 }}>VALIDATION CHECKLIST</div>
              <div>⬜  Panel square: ContentPanel breathing zone sufficient with photo (skillH=148, breathing≈108px)</div>
              <div>⬜  Panel square: Dir C name "JOHN\nDOE" at 42px fits breathing zone (est. 88px in 108px)</div>
              <div>⬜  Panel portrait/story: ratios 55%/55% — content panel has enough room for all 3 directions</div>
              <div>⬜  Full bleed: player name hero (96px) readable; dual-gradient top vignette doesn't block crest</div>
              <div>⬜  Cinematic (no photo): ghost initials "JD" visible at opacity 0.045 in face-zone (~top 18%)</div>
              <div>⬜  Cinematic: bottom content stack (656px) fits cleanly within dark gradient fade area</div>
              <div>⬜  Split: ContentPanel height distributes via flex:1 without hardcoded value</div>
              <div style={{ color:"#86efac" }}>✓   Banner: 2-LINE "LION FOOTBALL\nACADEMY" at 76px — VALIDATED SAFE (≈494px max line in 600px inner)</div>
              <div>⬜  Banner Dir C: "JOHN DOE" at 88px single-line, no sandwich text — visual rhythm clean</div>
              <div>⬜  Banner: 1.5px accent dividers visible and rhythmically balanced at 500px height</div>
              <div>⬜  Banner: skills 2×2 at 46px score readable in 400px column × 500px height</div>
              <div style={{ color:"#86efac" }}>✓   Band: stats strip widened to 220px — score 36px + label 10px + dot 10px improves readability</div>
              <div>⬜  Band: overlay content (headline + tags) readable over gradient at 640px width</div>
              <div>⬜  All (no photo): ghost initials / gradient fallback aesthetically acceptable for each layout</div>
              <div>⬜  All: position chip contrast acceptable across A (blue/gold) / B (blue solid) / C (purple) directions</div>
              <div>⬜  All: Bebas Neue / Barlow Condensed loaded (check number metrics vs system fallback)</div>
            </div>
          </div>

        </div>
      </div>
    </>
  );
}
