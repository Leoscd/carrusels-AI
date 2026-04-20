import { useState, useRef } from 'react';
import html2canvas from 'html2canvas';
import { Download, Plus, Trash2, Image as ImageIcon } from 'lucide-react';
import './index.css';

const DEFAULT_SLIDES = [
  {
    id: 1,
    type: 'cover',
    title: 'Presupuesto completo en la obra <span class="highlight">sin volver a la PC</span>',
    subtitle: 'Remote Claude Code',
    subtext: 'Arquitectura impulsada por IA aplicada',
    image: 'https://images.unsplash.com/photo-1503387762-592deb58ef4e?auto=format&fit=crop&q=80&w=1000'
  },
  {
    id: 2,
    type: 'steps',
    title: 'Configuración <br><span class="highlight">del entorno remoto</span>',
    subtitle: 'La Infraestructura',
    steps: [
      { id: 1, title: '01. Estación Base', text: 'Inicia la instancia de Claude Code en tu terminal local.' },
      { id: 2, title: '02. Tunelización', text: 'Activa el acceso seguro mediante el comando /remote.' },
      { id: 3, title: '03. Control Móvil', text: 'Vincula tu dispositivo y opera con toda tu base de datos.' }
    ]
  },
  {
    id: 3,
    type: 'cta',
    title: '¿Sigues presupuestando <br>de forma manual?',
    subtext: 'Optimiza tu estudio con Remote Claude Code.',
    cta: 'CONSULTA POR DM'
  }
];

function App() {
  const [slides, setSlides] = useState(DEFAULT_SLIDES);
  const [isExporting, setIsExporting] = useState(false);
  const carouselRef = useRef(null);

  const addSlide = (type) => {
    const newSlide = {
      id: Date.now(),
      type,
      title: 'Nuevo Titulo <span class="highlight">Destacado</span>',
      subtitle: type === 'cover' || type === 'steps' ? 'Subtítulo' : '',
      subtext: type === 'cover' || type === 'cta' ? 'Texto descriptivo' : '',
      image: type === 'cover' ? 'https://images.unsplash.com/photo-1541888086425-d81bb19240f5?auto=format&fit=crop&w=1000' : '',
      steps: type === 'steps' ? [{ id: Date.now()+1, title: 'Paso 1', text: 'Descripción del paso' }] : undefined,
      cta: type === 'cta' ? 'CALL TO ACTION' : undefined
    };
    setSlides([...slides, newSlide]);
  };

  const updateSlide = (id, field, value) => {
    setSlides(slides.map(s => s.id === id ? { ...s, [field]: value } : s));
  };

  const removeSlide = (id) => {
    setSlides(slides.filter(s => s.id !== id));
  };

  const exportSlides = async () => {
    if (!carouselRef.current) return;
    setIsExporting(true);
    
    try {
      // Small pause to let fonts load properly if not already
      await new Promise(r => setTimeout(r, 500));
      
      const slideNodes = carouselRef.current.querySelectorAll('.slide-card');
      
      for (let i = 0; i < slideNodes.length; i++) {
        const slide = slideNodes[i];
        
        const canvas = await html2canvas(slide, {
          scale: 2,
          backgroundColor: '#050505',
          useCORS: true,
          logging: false
        });
        
        const link = document.createElement('a');
        link.download = `carrusel_premium_slide_0${i + 1}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
        
        await new Promise(r => setTimeout(r, 500));
      }
    } catch (err) {
      console.error('Error exporting', err);
      alert('Hubo un error al exportar.');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>
      
      {/* Editor Sidebar */}
      <div style={{ width: '450px', background: '#0a0a0a', borderRight: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto', padding: '24px' }}>
        <div style={{ marginBottom: '32px' }}>
          <h1 style={{ fontFamily: 'Montserrat', fontSize: '24px', fontWeight: 600, margin: 0, color: '#f6c618' }}>Carrusels AI</h1>
          <p style={{ color: '#777', margin: '4px 0 0 0', fontSize: '14px' }}>Generador Premium</p>
        </div>

        <div style={{ display: 'flex', gap: '10px', marginBottom: '24px' }}>
          <button className="btn-primary" onClick={exportSlides} disabled={isExporting} style={{ flexGrow: 1, justifyContent: 'center' }}>
            <Download size={16} /> {isExporting ? 'EXPORTANDO...' : 'EXPORTAR PNG'}
          </button>
        </div>

        <div style={{ display: 'flex', gap: '8px', marginBottom: '32px', flexWrap: 'wrap' }}>
          <button className="btn-primary" onClick={() => addSlide('cover')} style={{ flex: '1 1 45%', padding: '8px', fontSize: '11px' }}>+ PORTADA</button>
          <button className="btn-primary" onClick={() => addSlide('steps')} style={{ flex: '1 1 45%', padding: '8px', fontSize: '11px' }}>+ PASOS</button>
          <button className="btn-primary" onClick={() => addSlide('cta')} style={{ flex: '1 1 45%', padding: '8px', fontSize: '11px' }}>+ CTA FINAL</button>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {slides.map((slide, index) => (
            <div key={slide.id} className="panel">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span style={{ color: '#f6c618', fontFamily: 'Montserrat', fontSize: '12px', letterSpacing: '1px' }}>SLIDE 0{index + 1} - {slide.type.toUpperCase()}</span>
                <button onClick={() => removeSlide(slide.id)} style={{ background: 'none', border: 'none', color: '#ff4444', cursor: 'pointer', padding: '4px' }}>
                  <Trash2 size={14} />
                </button>
              </div>

              {['cover', 'steps'].includes(slide.type) && (
                <input 
                  className="input-modern" 
                  style={{ minHeight: 'auto', padding: '10px' }} 
                  placeholder="Subtítulo Superior" 
                  value={slide.subtitle} 
                  onChange={e => updateSlide(slide.id, 'subtitle', e.target.value)} 
                />
              )}

              <input 
                className="input-modern" 
                style={{ minHeight: 'auto', padding: '10px' }} 
                placeholder='Título (usa <span class="highlight">texto</span>)' 
                value={slide.title} 
                onChange={e => updateSlide(slide.id, 'title', e.target.value)} 
              />

              {['cover', 'cta'].includes(slide.type) && (
                <textarea 
                  className="input-modern" 
                  style={{ minHeight: '80px', padding: '10px' }} 
                  placeholder="Subtexto (bajo el título)" 
                  value={slide.subtext} 
                  onChange={e => updateSlide(slide.id, 'subtext', e.target.value)} 
                />
              )}

              {slide.type === 'cover' && (
                <input 
                  className="input-modern" 
                  style={{ minHeight: 'auto', padding: '10px' }} 
                  placeholder="URL Imagen Unsplash" 
                  value={slide.image} 
                  onChange={e => updateSlide(slide.id, 'image', e.target.value)} 
                />
              )}

              {slide.type === 'cta' && (
                <input 
                  className="input-modern" 
                  style={{ minHeight: 'auto', padding: '10px' }} 
                  placeholder="Texto Botón CTA" 
                  value={slide.cta} 
                  onChange={e => updateSlide(slide.id, 'cta', e.target.value)} 
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Preview Area */}
      <div style={{ flexGrow: 1, background: '#000', overflow: 'auto', padding: '40px', display: 'flex', justifyContent: 'center' }}>
        <div 
          id="carousel-preview" 
          ref={carouselRef}
          style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(1080px, 1080px))', 
            gap: '50px', 
            transformOrigin: 'top center',
            transform: 'scale(0.35)',
            width: 'max-content'
          }}
        >
          {slides.map((slide, index) => (
            <div key={slide.id} className="slide-card">
              <div className="inner-frame"></div>
              
              <div className="content" style={{ textAlign: slide.type === 'cta' ? 'center' : 'left', alignItems: slide.type === 'cta' ? 'center' : 'flex-start' }}>
                
                {slide.type === 'cover' && slide.image && (
                  <img src={slide.image} className="slide-img" alt="Portada" />
                )}

                {slide.subtitle && <h2>{slide.subtitle}</h2>}
                
                {/* We use dangerouslySetInnerHTML to allow <span class="highlight"> formatting */}
                <h1 dangerouslySetInnerHTML={{ __html: slide.title }}></h1>
                
                {slide.subtext && <p className="subtext" style={{ marginBottom: slide.type === 'cta' ? '70px' : '0' }}>{slide.subtext}</p>}

                {slide.type === 'steps' && slide.steps && (
                  <div style={{ width: '100%', marginTop: '30px' }}>
                    {slide.steps.map(step => (
                      <div key={step.id} className="step-box">
                        <h3>{step.title}</h3>
                        <p>{step.text}</p>
                      </div>
                    ))}
                  </div>
                )}

                {slide.type === 'cta' && (
                  <div className="cta-box" style={{ width: '80%' }}>
                    <p>{slide.cta}</p>
                  </div>
                )}

              </div>

              <div className="footer">
                <div className="handle">{slide.type === 'cta' ? 'soyleoai.com' : '@soy.leo_ai'}</div>
                <div className="slide-number">0{index + 1}</div>
              </div>
            </div>
          ))}
        </div>
      </div>
    
    </div>
  );
}

export default App;
