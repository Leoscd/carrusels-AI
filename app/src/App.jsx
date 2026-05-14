import { useState, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Download, Trash2 } from 'lucide-react';
import './index.css';

const DEFAULT_SLIDES = [
  {
    id: 1, type: 'cover',
    label: 'ARQUITECTURA + IA',
    title: 'PRESUPUESTO COMPLETO EN OBRA SIN VOLVER A LA PC',
    kicker: 'Claude Code aplicado a estudios de arquitectura'
  },
  {
    id: 2, type: 'steps',
    label: 'CÓMO FUNCIONA',
    title: 'TRES PASOS PARA EMPEZAR',
    steps: [
      { id: 1, paso: 'PASO 01', text: 'Iniciá Claude Code en tu terminal local.' },
      { id: 2, paso: 'PASO 02', text: 'Activá el acceso remoto con el comando /remote.' },
      { id: 3, paso: 'PASO 03', text: 'Operá desde el celular en cualquier obra.' }
    ]
  },
  {
    id: 3, type: 'lista',
    label: 'LO QUE CAMBIA',
    title: 'VENTAJAS INMEDIATAS',
    items: [
      { id: 1, num: '01', text: 'Respondés consultas de obra sin abrir la laptop.' },
      { id: 2, num: '02', text: 'Generás presupuestos en segundos desde el celular.' },
      { id: 3, num: '03', text: 'Tu estudio funciona aunque no estés en él.' }
    ]
  },
  {
    id: 4, type: 'cta',
    title: '¿SEGUÍS PRESUPUESTANDO DE FORMA MANUAL?',
    subtext: 'Optimizá tu estudio con Remote Claude Code.',
    cta: 'CONSULTA POR DM'
  }
];

function newSlide(type) {
  const base = { id: Date.now(), type };
  if (type === 'cover')    return { ...base, label: 'LABEL', title: 'TÍTULO PRINCIPAL DEL SLIDE', kicker: 'Texto descriptivo secundario' };
  if (type === 'steps')    return { ...base, label: 'CÓMO FUNCIONA', title: 'PASOS CLAVE', steps: [{ id: Date.now()+1, paso: 'PASO 01', text: 'Describí el primer paso aquí.' }] };
  if (type === 'lista')    return { ...base, label: 'PUNTOS CLAVE', title: 'TÍTULO DE LA LISTA', items: [{ id: Date.now()+1, num: '01', text: 'Primer item de la lista.' }] };
  if (type === 'stat')     return { ...base, label: 'EN NÚMEROS', stat1: '3X', stat1desc: 'más rápido', stat2: '80%', stat2desc: 'menos tiempo manual' };
  if (type === 'columnas') return { ...base, col1_label: 'ANALIZAR', col1_sub: 'ETAPA 01', col2_label: 'DISEÑAR', col2_sub: 'ETAPA 02', col3_label: 'ENTREGAR', col3_sub: 'ETAPA 03' };
  if (type === 'cta')      return { ...base, title: '¿LISTO PARA DAR EL SIGUIENTE PASO?', subtext: 'Consultá cómo implementarlo en tu estudio.', cta: 'CONSULTA POR DM' };
  return base;
}

export default function App() {
  const [slides, setSlides] = useState(DEFAULT_SLIDES);
  const [exporting, setExporting] = useState(false);
  const previewRef = useRef(null);

  const addSlide  = (type) => setSlides(s => [...s, newSlide(type)]);
  const removeSlide = (id) => setSlides(s => s.filter(sl => sl.id !== id));
  const updateSlide = (id, patch) => setSlides(s => s.map(sl => sl.id === id ? { ...sl, ...patch } : sl));

  const updateStep = (slideId, stepId, patch) =>
    setSlides(s => s.map(sl => sl.id === slideId
      ? { ...sl, steps: sl.steps.map(st => st.id === stepId ? { ...st, ...patch } : st) }
      : sl));

  const updateItem = (slideId, itemId, patch) =>
    setSlides(s => s.map(sl => sl.id === slideId
      ? { ...sl, items: sl.items.map(it => it.id === itemId ? { ...it, ...patch } : it) }
      : sl));

  const exportAll = async () => {
    if (!previewRef.current) return;
    setExporting(true);
    try {
      await new Promise(r => setTimeout(r, 300));
      const nodes = previewRef.current.querySelectorAll('.slide-card');
      for (let i = 0; i < nodes.length; i++) {
        const isCta = nodes[i].classList.contains('cta-slide');
        const canvas = await html2canvas(nodes[i], {
          scale: 2,
          backgroundColor: isCta ? '#EB4604' : '#171614',
          useCORS: true,
          logging: false
        });
        const a = document.createElement('a');
        a.download = `slide_0${i + 1}.png`;
        a.href = canvas.toDataURL('image/png');
        a.click();
        await new Promise(r => setTimeout(r, 400));
      }
    } catch (e) {
      alert('Error al exportar: ' + e.message);
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="sidebar-title">CARRUSELS AI</h1>
          <p className="sidebar-sub">@soy.leo_ai</p>
        </div>

        <button className="btn-primary" onClick={exportAll} disabled={exporting}>
          <Download size={16} /> {exporting ? 'EXPORTANDO...' : 'EXPORTAR PNG'}
        </button>

        <div className="add-slide-grid">
          {['cover','steps','lista','stat','columnas','cta'].map(t => (
            <button key={t} className="btn-secondary" onClick={() => addSlide(t)}>+ {t.toUpperCase()}</button>
          ))}
        </div>

        <div className="editor-list">
          {slides.map((slide, i) => (
            <SlideEditor
              key={slide.id}
              slide={slide}
              index={i}
              onUpdate={patch => updateSlide(slide.id, patch)}
              onUpdateStep={(stepId, patch) => updateStep(slide.id, stepId, patch)}
              onUpdateItem={(itemId, patch) => updateItem(slide.id, itemId, patch)}
              onRemove={() => removeSlide(slide.id)}
            />
          ))}
        </div>
      </aside>

      <main className="preview-area">
        <div
          ref={previewRef}
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '50px',
            transform: 'scale(0.35)',
            transformOrigin: 'top center',
            width: 'var(--slide-w)',
          }}
        >
          {slides.map((slide, i) => (
            <SlidePreview key={slide.id} slide={slide} index={i} />
          ))}
        </div>
      </main>
    </div>
  );
}

function SlideEditor({ slide, index, onUpdate, onUpdateStep, onUpdateItem, onRemove }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="panel">
      <div className="panel-header">
        <button className="panel-toggle" onClick={() => setOpen(!open)}>
          <span className="panel-label">SLIDE 0{index + 1} — {slide.type.toUpperCase()}</span>
          <span style={{ color: 'var(--moss)', fontSize: '12px' }}>{open ? '▲' : '▼'}</span>
        </button>
        <button className="btn-remove" onClick={onRemove}><Trash2 size={14} /></button>
      </div>

      {open && (
        <div className="panel-fields">
          {!['cta','columnas','stat'].includes(slide.type) && (
            <input className="input-modern" placeholder="LABEL" value={slide.label || ''} onChange={e => onUpdate({ label: e.target.value })} />
          )}

          {['cover','steps','lista'].includes(slide.type) && (
            <input className="input-modern" placeholder="Título" value={slide.title || ''} onChange={e => onUpdate({ title: e.target.value })} />
          )}

          {slide.type === 'cover' && (
            <textarea className="input-modern" placeholder="Kicker / subtexto" value={slide.kicker || ''} onChange={e => onUpdate({ kicker: e.target.value })} style={{ minHeight: '80px' }} />
          )}

          {slide.type === 'steps' && (slide.steps || []).map((step, si) => (
            <div key={step.id} className="sub-panel">
              <input className="input-modern" placeholder={`PASO 0${si+1}`} value={step.paso} onChange={e => onUpdateStep(step.id, { paso: e.target.value })} />
              <textarea className="input-modern" placeholder="Texto" value={step.text} onChange={e => onUpdateStep(step.id, { text: e.target.value })} style={{ minHeight: '60px' }} />
            </div>
          ))}

          {slide.type === 'lista' && (slide.items || []).map((item, ii) => (
            <div key={item.id} className="sub-panel">
              <div style={{ display: 'flex', gap: '8px' }}>
                <input className="input-modern" placeholder={`0${ii+1}`} value={item.num} onChange={e => onUpdateItem(item.id, { num: e.target.value })} style={{ width: '70px', flexShrink: 0 }} />
                <textarea className="input-modern" placeholder="Texto del item" value={item.text} onChange={e => onUpdateItem(item.id, { text: e.target.value })} style={{ minHeight: '60px' }} />
              </div>
            </div>
          ))}

          {slide.type === 'stat' && (
            <>
              <input className="input-modern" placeholder="Número grande (ej: 3X)" value={slide.stat1 || ''} onChange={e => onUpdate({ stat1: e.target.value })} />
              <input className="input-modern" placeholder="Descripción stat 1" value={slide.stat1desc || ''} onChange={e => onUpdate({ stat1desc: e.target.value })} />
              <input className="input-modern" placeholder="Segundo número (ej: 80%)" value={slide.stat2 || ''} onChange={e => onUpdate({ stat2: e.target.value })} />
              <input className="input-modern" placeholder="Descripción stat 2" value={slide.stat2desc || ''} onChange={e => onUpdate({ stat2desc: e.target.value })} />
            </>
          )}

          {slide.type === 'columnas' && (
            <>
              {[['col1','NIGHT (izq)'],['col2','NARANJA (centro)'],['col3','CREAM (der)']].map(([key, hint]) => (
                <div key={key} className="sub-panel">
                  <input className="input-modern" placeholder={`${hint} — Label vertical`} value={slide[`${key}_label`] || ''} onChange={e => onUpdate({ [`${key}_label`]: e.target.value })} />
                  <input className="input-modern" placeholder={`${hint} — Subtítulo`} value={slide[`${key}_sub`] || ''} onChange={e => onUpdate({ [`${key}_sub`]: e.target.value })} />
                </div>
              ))}
            </>
          )}

          {slide.type === 'cta' && (
            <>
              <input className="input-modern" placeholder="Título CTA" value={slide.title || ''} onChange={e => onUpdate({ title: e.target.value })} />
              <textarea className="input-modern" placeholder="Subtexto" value={slide.subtext || ''} onChange={e => onUpdate({ subtext: e.target.value })} style={{ minHeight: '80px' }} />
              <input className="input-modern" placeholder="Texto botón (ej: CONSULTA POR DM)" value={slide.cta || ''} onChange={e => onUpdate({ cta: e.target.value })} />
            </>
          )}
        </div>
      )}
    </div>
  );
}

function SlidePreview({ slide, index }) {
  const isCta      = slide.type === 'cta';
  const isColumnas = slide.type === 'columnas';

  return (
    <div className={`slide-card${isCta ? ' cta-slide' : ''}`} style={isColumnas ? { padding: 0 } : {}}>

      {!isColumnas && !isCta && (
        <>
          <div className="slide-header">
            {slide.label && <span className="slide-header-label">{slide.label}</span>}
            <span className="slide-header-num">0{index + 1}</span>
          </div>
          <div className="slide-rule" />
        </>
      )}

      {slide.type === 'cover'    && <CoverContent    slide={slide} />}
      {slide.type === 'steps'    && <StepsContent    slide={slide} />}
      {slide.type === 'lista'    && <ListaContent    slide={slide} />}
      {slide.type === 'stat'     && <StatContent     slide={slide} />}
      {slide.type === 'columnas' && <ColumnasContent slide={slide} index={index} />}
      {slide.type === 'cta'      && <CtaContent      slide={slide} />}

      {!isColumnas && !isCta && (
        <div className="footer">
          <span className="handle">@soy.leo_ai</span>
          <span className="slide-number">0{index + 1}</span>
        </div>
      )}
    </div>
  );
}

function CoverContent({ slide }) {
  return (
    <div className="cover-content">
      {slide.label && <div className="label-tag">{slide.label}</div>}
      <h1 className="slide-h1">{slide.title}</h1>
      {slide.kicker && <p className="slide-kicker">{slide.kicker}</p>}
    </div>
  );
}

function StepsContent({ slide }) {
  return (
    <div className="steps-content">
      <h2 className="slide-h2">{slide.title}</h2>
      <div className="steps-list">
        {(slide.steps || []).map(step => (
          <div key={step.id} className="step-box">
            <div className="paso-label">{step.paso}</div>
            <p className="step-text">{step.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function ListaContent({ slide }) {
  return (
    <div className="lista-content">
      <h2 className="slide-h2">{slide.title}</h2>
      <div className="lista-list">
        {(slide.items || []).map(item => (
          <div key={item.id} className="lista-item">
            <span className="lista-num">{item.num}</span>
            <p className="lista-text">{item.text}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatContent({ slide }) {
  return (
    <div className="stat-content">
      {slide.stat1 && (
        <div className="stat-block">
          <div className="stat-number">{slide.stat1}</div>
          {slide.stat1desc && <p className="stat-desc">{slide.stat1desc}</p>}
        </div>
      )}
      {slide.stat1 && slide.stat2 && <div className="stat-divider" />}
      {slide.stat2 && (
        <div className="stat-block">
          <div className="stat-number">{slide.stat2}</div>
          {slide.stat2desc && <p className="stat-desc">{slide.stat2desc}</p>}
        </div>
      )}
    </div>
  );
}

function ColumnasContent({ slide, index }) {
  const cols = [
    { label: slide.col1_label || 'ETAPA 01', sub: slide.col1_sub || '', bg: '#171614', color: '#FFFFFF', style: { borderRight: '3px solid #EB4604' } },
    { label: slide.col2_label || 'ETAPA 02', sub: slide.col2_sub || '', bg: '#EB4604', color: '#171614', style: {} },
    { label: slide.col3_label || 'ETAPA 03', sub: slide.col3_sub || '', bg: '#F5F0E8', color: '#171614', style: { borderLeft: '3px solid #171614' } }
  ];
  return (
    <div className="columnas-layout">
      {cols.map((col, i) => (
        <div key={i} className="columna" style={{ background: col.bg, ...col.style }}>
          <div className="columna-bottom">
            {col.sub && <p className="columna-sub" style={{ color: col.color }}>{col.sub}</p>}
            <div className="columna-handle" style={{ color: col.color }}>@soy.leo_ai · 0{index + 1}</div>
          </div>
          <span className="columna-label" style={{ color: col.color }}>{col.label}</span>
        </div>
      ))}
    </div>
  );
}

function CtaContent({ slide }) {
  return (
    <div className="cta-content">
      <h1 className="cta-h1">{slide.title}</h1>
      {slide.subtext && <p className="cta-sub">{slide.subtext}</p>}
      {slide.cta && <div className="cta-btn">{slide.cta}</div>}
      <span className="cta-handle">@soy.leo_ai</span>
    </div>
  );
}
