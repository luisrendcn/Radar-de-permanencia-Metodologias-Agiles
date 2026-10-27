import { type ReactNode, useMemo, useState } from 'react';
import { QueryClient, QueryClientProvider, useQueryClient } from '@tanstack/react-query';
import { Link, Route, Switch, useLocation, Router as WouterRouter } from 'wouter';
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, BarChart3,
  Check, CheckCircle2, CircleHelp, Database, FileSpreadsheet, Filter, Gauge, ClipboardList,
  Layers3, Menu, ShieldCheck, Sparkles, Target, TrendingDown, Users,
} from 'lucide-react';
import {
  useHealthCheck, useGetDatasetStatus, useGenerateDemoData, useUploadDataset,
  useSaveDatasetMapping, useValidateDataset, useRunDatasetEtl, useGetAnalyticsOverview,
  useGetTurnoverAnalytics, useGetDiagnosticAnalytics, useGetCostSettings, useUpdateCostSettings,
  useGetModelStatus, useTrainModel, usePredictCandidateRisk, useGetFairnessStatus,
  getHealthCheckQueryKey, getGetDatasetStatusQueryKey, getGetAnalyticsOverviewQueryKey,
  getGetTurnoverAnalyticsQueryKey, getGetDiagnosticAnalyticsQueryKey, getGetCostSettingsQueryKey,
  getGetModelStatusQueryKey, getGetFairnessStatusQueryKey,
  type CandidateInput, type CandidatePrediction, type UploadPreview, type ValidationReport,
} from '@workspace/api-client-react';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import './index.css';

const queryClient = new QueryClient();
type FilterState = { campaign: string; shift: string; supervisor: string; startMonth: string; endMonth: string };
const blankFilters: FilterState = { campaign: '', shift: '', supervisor: '', startMonth: '', endMonth: '' };
const fmt = (n?: number | null, digits = 1) => n == null ? '—' : `${new Intl.NumberFormat('es-CO', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Number(n))}%`;
const fmtRate = (n?: number | null, digits = 1) => n == null ? '—' : fmt(Number(n) * 100, digits);
const fmtValue = (n?: number | null, digits = 2) => n == null ? '—' : new Intl.NumberFormat('es-CO', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Number(n));
const fmtSigned = (n?: number | null, digits = 2) => n == null ? '—' : `${n > 0 ? '+' : ''}${new Intl.NumberFormat('es-CO', { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(Number(n))}`;
const number = (n?: number | null) => n == null ? '—' : new Intl.NumberFormat('es-CO').format(n);
const date = (value?: string | null) => value ? new Date(value).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' }) : 'Sin fecha';
const errText = (e: unknown) => e instanceof Error ? e.message : 'No fue posible completar la solicitud.';

function Shell({ children, synthetic }: { children: ReactNode; synthetic: boolean }) {
  const [location] = useLocation();
  const [mobileOpen, setMobileOpen] = useState(false);
  const links = [
    { href: '/', label: 'Resumen', icon: BarChart3 },
    { href: '/rotacion', label: 'Rotación', icon: TrendingDown },
    { href: '/diagnostico', label: 'Diagnóstico', icon: Activity },
    { href: '/candidato', label: 'Evaluación de apoyo', icon: Users },
    { href: '/datos', label: 'Datos', icon: Database },
    { href: '/modelo', label: 'Modelo y equidad', icon: Gauge },
  ];
  const retrospective = { href: '/retrospectiva', label: 'Retrospectiva del proyecto', icon: ClipboardList };
  const currentLabel = location === retrospective.href ? retrospective.label : links.find(l => l.href === location)?.label ?? 'Radar';
  return <div className="app-shell">
    <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Activity size={19}/></div><div><b>RADAR</b><span>PEOPLE ANALYTICS</span></div></div>
      <div className="workspace-label">ESPACIO DE TRABAJO</div>
      <nav aria-label="Navegación principal">{links.map(({ href, label, icon: Icon }) =>
        <Link href={href} key={href} onClick={() => setMobileOpen(false)} className={`nav-link ${location === href ? 'active' : ''}`} data-testid={`link-nav-${href.replace('/', '') || 'resumen'}`}>
          <Icon size={18} strokeWidth={1.8}/><span>{label}</span>{location === href && <span className="nav-indicator"/>}
        </Link>)}
        <div className="sidebar-divider"/>
        <div className="workspace-label sidebar-secondary-label">PROYECTO</div>
        <Link href={retrospective.href} onClick={() => setMobileOpen(false)} className={`nav-link nav-link-secondary ${location === retrospective.href ? 'active' : ''}`} data-testid="link-nav-retrospectiva">
          <ClipboardList size={18} strokeWidth={1.8}/><span>{retrospective.label}</span>{location === retrospective.href && <span className="nav-indicator"/>}
        </Link>
      </nav>
      <div className="sidebar-foot">
        <div className="privacy-mark"><ShieldCheck size={17}/><span>Uso responsable</span></div>
        <p>Sin decisiones automatizadas.<br/>Datos analíticos agregados.</p>
        <div className="sidebar-version"><span className="pulse-dot"/> Servicio de análisis</div>
      </div>
    </aside>
    {mobileOpen && <button className="mobile-scrim" aria-label="Cerrar menú" onClick={() => setMobileOpen(false)}/>}
    <main className="main-frame">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="Abrir menú" onClick={() => setMobileOpen(!mobileOpen)}><Menu size={20}/></button>
        <div className="crumb"><span>PERSONAS</span><span className="crumb-divider">/</span><strong>{currentLabel}</strong></div>
        <div className="top-meta"><span className={`system-status ${location === retrospective.href ? '' : 'api-unavailable'}`}><span className="pulse-dot"/> {location === retrospective.href ? 'Retrospectiva' : 'API no configurada'}</span><span className="top-date">{new Date().toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' })}</span></div>
      </header>
      {synthetic && <div className="synthetic-banner" role="status"><Sparkles size={15}/><span><strong>Datos sintéticos</strong> · Este análisis utiliza información de demostración. No representa personas ni resultados reales.</span><span className="synthetic-tag">ENTORNO DEMO</span></div>}
      <div className="page-area">{children}</div>
      <footer className="footer"><span>Radar de Permanencia</span><span>Analítica para comprender. Criterio humano para decidir.</span></footer>
    </main>
  </div>;
}

function PageTitle({ eyebrow, title, subtitle, action }: { eyebrow: string; title: string; subtitle: string; action?: ReactNode }) {
  return <div className="page-title"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{subtitle}</p></div>{action && <div className="title-action">{action}</div>}</div>;
}
function Panel({ title, subtitle, children, action, className = '' }: { title: string; subtitle?: string; children: ReactNode; action?: ReactNode; className?: string }) {
  return <section className={`panel ${className}`}><div className="panel-head"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>{children}</section>;
}
function StateMessage({ loading, error, empty, retry }: { loading?: boolean; error?: unknown; empty?: boolean; retry?: () => void }) {
  if (loading) return <div className="state-box"><div className="skeleton-line wide"/><div className="skeleton-line"/><div className="skeleton-line short"/></div>;
  if (error) return <div className="state-box error-state"><AlertCircle size={19}/><span>{errText(error)}</span>{retry && <button className="text-button" onClick={retry}>Reintentar</button>}</div>;
  if (empty) return <div className="state-box empty-state"><Database size={20}/><strong>Sin información disponible</strong><span>Cuando haya datos procesados, aparecerán aquí.</span></div>;
  return null;
}
function Button({ children, onClick, disabled, kind = 'primary', type = 'button' }: { children: ReactNode; onClick?: () => void; disabled?: boolean; kind?: 'primary' | 'secondary' | 'quiet'; type?: 'button' | 'submit' }) {
  return <button type={type} className={`button ${kind}`} onClick={onClick} disabled={disabled}>{children}</button>;
}
function Metric({ label, value, detail, icon: Icon, tone = '' }: { label: string; value: ReactNode; detail?: ReactNode; icon: typeof Users; tone?: string }) {
  return <div className={`metric-card ${tone}`}><div className="metric-top"><span>{label}</span><Icon size={17}/></div><strong className="metric-value">{value}</strong>{detail && <div className="metric-detail">{detail}</div>}</div>;
}

function OverviewPage() {
  const qc = useQueryClient();
  const health = useHealthCheck({ query: { queryKey: getHealthCheckQueryKey() } });
  const { data, isLoading, error, refetch } = useGetAnalyticsOverview({ query: { queryKey: getGetAnalyticsOverviewQueryKey() } });
  const dataset = useGetDatasetStatus({ query: { queryKey: getGetDatasetStatusQueryKey() } });
  const demo = useGenerateDemoData();
  const refresh = () => { void qc.invalidateQueries({ queryKey: getGetAnalyticsOverviewQueryKey() }); void qc.invalidateQueries({ queryKey: getGetDatasetStatusQueryKey() }); };
  const canLoadDemo = !dataset.data?.processed;
  return <div className="content">
    <PageTitle eyebrow="VISIÓN EJECUTIVA · 01" title="La permanencia, en contexto." subtitle="Una lectura clara de la rotación temprana para entender dónde enfocar la conversación." action={<div className="period-pill"><span className="live-mark"/>{data?.datasetReady ? 'Datos procesados' : 'Esperando datos'}</div>}/>
    <StateMessage loading={isLoading} error={error} retry={() => void refetch()}/>
    {!isLoading && !error && !data?.datasetReady && <div className="setup-strip"><div className="setup-symbol"><Database size={19}/></div><div><b>El análisis aún no tiene una base procesada</b><span>Importa tus fuentes en Datos o genera datos de demostración para explorar la herramienta.</span></div><Link className="setup-link" href="/datos">Ir a datos <ArrowRight size={15}/></Link>{canLoadDemo && <Button kind="secondary" disabled={demo.isPending} onClick={() => demo.mutate(undefined, { onSuccess: refresh })}>{demo.isPending ? 'Generando…' : 'Generar demo'}</Button>}</div>}
    {data?.datasetReady && <>
      <div className="metric-grid">
        <Metric label="ROTACIÓN TEMPRANA" value={fmtRate(data.turnoverRate)} detail={<span className="trend-note">{data.previousRate != null ? <>{data.turnoverRate != null && data.turnoverRate > data.previousRate ? <ArrowUpRight size={14}/> : <ArrowDownRight size={14}/>} Frente al periodo anterior: {fmtRate(data.previousRate)}</> : 'Tasa sobre población elegible'}</span>} icon={TrendingDown} tone="metric-emphasis"/>
        <Metric label="INGRESOS EN COHORTE" value={number(data.totalHires)} detail="Personas vinculadas en el periodo" icon={Users}/>
        <Metric label="RENUNCIAS TEMPRANAS" value={number(data.earlyResignations)} detail="Eventos observados antes del umbral" icon={ArrowDownRight}/>
        <Metric label="POBLACIÓN ELEGIBLE" value={number(data.eligibleEmployees)} detail={`${number(data.censoredEmployees)} observaciones censuradas`} icon={Target}/>
      </div>
      <div className="overview-grid">
        <Panel title="Señales para revisar" subtitle="Pistas que orientan el análisis; no son conclusiones causales." className="highlights-panel">
          {data.highlights.length ? <div className="highlight-list">{data.highlights.map((item, i) => <div className="highlight-row" key={`${item}-${i}`}><span className="highlight-index">0{i + 1}</span><span>{item}</span><ArrowRight size={15}/></div>)}</div> : <div className="empty-inline">No hay señales destacadas para este conjunto.</div>}
        </Panel>
        <Panel title="Lectura del periodo" subtitle="Contexto mínimo antes de comparar cifras." className="period-panel">
          <div className="period-stat"><span>Mes crítico observado</span><strong>{data.criticalMonth != null ? `Mes ${data.criticalMonth}` : 'No identificado'}</strong></div>
          <div className="period-stat"><span>Modelo disponible</span><strong className="status-text">{data.modelTrained ? 'Entrenado' : 'Sin entrenar'}</strong></div>
          <div className="period-stat"><span>Salidas involuntarias excluidas</span><strong>{number(data.involuntaryExits)}</strong></div>
          <div className="source-note"><CircleHelp size={15}/> La tasa se calcula sobre la población elegible; las observaciones sin ventana completa se reportan aparte.</div>
        </Panel>
      </div>
    </>}
    <div className="health-line"><span className={`health-dot ${health.data?.status === 'ok' ? 'good' : ''}`}/>{health.isLoading ? 'Comprobando servicio…' : health.error ? 'Estado del servicio no disponible' : `Servicio ${health.data?.status ?? 'activo'}`}<span className="health-sep">·</span> {dataset.data?.processed ? `${number(dataset.data.totalHires)} registros de contratación disponibles` : 'Sin conjunto procesado'}</div>
  </div>;
}

function Filters({ filters, setFilters, options }: { filters: FilterState; setFilters: (x: FilterState) => void; options?: { campaigns: string[]; shifts: string[]; supervisors: string[] } }) {
  const update = (key: keyof FilterState, value: string) => setFilters({ ...filters, [key]: value });
  return <div className="filters-bar"><div className="filter-label"><Filter size={15}/> FILTROS COMPARTIDOS</div>
    <label>Campaña<select aria-label="Filtrar por campaña" value={filters.campaign} onChange={e => update('campaign', e.target.value)}><option value="">Todas</option>{(options?.campaigns ?? []).map(x => <option key={x}>{x}</option>)}</select></label>
    <label>Turno<select aria-label="Filtrar por turno" value={filters.shift} onChange={e => update('shift', e.target.value)}><option value="">Todos</option>{(options?.shifts ?? []).map(x => <option key={x}>{x}</option>)}</select></label>
    <label>Desde<input aria-label="Mes inicial" placeholder="AAAA-MM" value={filters.startMonth} onChange={e => update('startMonth', e.target.value)}/></label>
    <label>Hasta<input aria-label="Mes final" placeholder="AAAA-MM" value={filters.endMonth} onChange={e => update('endMonth', e.target.value)}/></label>
    <button className="filter-reset" onClick={() => setFilters(blankFilters)}>Limpiar</button>
  </div>;
}
function RateBar({ value }: { value: number | null }) {
  return <div className="rate-cell"><div className="rate-track"><span style={{ width: `${Math.min(100, Math.max(0, (value ?? 0) * 100))}%` }}/></div><b>{fmtRate(value)}</b></div>;
}
function TurnoverPage({ filters, setFilters }: { filters: FilterState; setFilters: (x: FilterState) => void }) {
  const params = useMemo(() => ({ campaign: filters.campaign || undefined, shift: filters.shift || undefined, supervisor: filters.supervisor || undefined, startMonth: filters.startMonth || undefined, endMonth: filters.endMonth || undefined }), [filters]);
  const queryKey = getGetTurnoverAnalyticsQueryKey(params);
  const { data, isLoading, error, refetch } = useGetTurnoverAnalytics(params, { query: { queryKey } });
  return <div className="content">
    <PageTitle eyebrow="PATRONES DE SALIDA · 02" title="Rotación por cohortes" subtitle="Compara periodos y antigüedad para ubicar cuándo se concentra la salida temprana."/>
    <Filters filters={filters} setFilters={setFilters} options={data?.availableFilters}/>
    <StateMessage loading={isLoading} error={error} empty={!isLoading && !error && !data} retry={() => void refetch()}/>
    {data && <>
      <div className="metric-grid compact-metrics"><Metric label="TASA FILTRADA" value={fmtRate(data.turnoverRate)} detail="Renuncias tempranas / elegibles" icon={TrendingDown} tone="metric-emphasis"/><Metric label="ELEGIBLES" value={number(data.eligible)} detail="Con ventana de observación completa" icon={Users}/><Metric label="RENUNCIAS" value={number(data.earlyResignations)} detail="Dentro del umbral temprano" icon={ArrowDownRight}/><Metric label="MES DE MAYOR SALIDA" value={data.criticalMonth ? `Mes ${data.criticalMonth}` : '—'} detail="Según la distribución observada" icon={Target}/></div>
      <div className="two-col">
        <Panel title="Cohortes de ingreso" subtitle="Tasa y volumen por periodo de vinculación.">
          {!data.cohorts.length ? <div className="empty-inline">No hay cohortes para los filtros elegidos.</div> : <div className="table-wrap"><table><thead><tr><th>COHORTE</th><th>INGRESOS</th><th>ELEGIBLES</th><th>RENUNCIAS</th><th>TASA TEMPRANA</th></tr></thead><tbody>{data.cohorts.map((c,i)=><tr key={`${c.cohort}-${i}`}><td><b>{c.cohort}</b>{c.critical && <span className="risk-label">PUNTO DE ATENCIÓN</span>}</td><td>{number(c.hires)}</td><td>{number(c.eligible)}</td><td>{number(c.earlyResignations)}</td><td><RateBar value={c.rate}/></td></tr>)}</tbody></table></div>}
        </Panel>
        <Panel title="Antigüedad de la salida" subtitle="Distribución de renuncias por mes de permanencia." className="tenure-panel">
          {data.tenureDistribution.length ? <div className="tenure-chart">{data.tenureDistribution.map(m=><div className="tenure-column" key={m.month}><div className="tenure-count">{number(m.resignations)}</div><div className="tenure-track"><span style={{ height: `${Math.max(3,Math.min(100,m.share))}%` }}/></div><small>M{m.month}</small></div>)}</div> : <div className="empty-inline">Sin distribución de antigüedad disponible.</div>}
          <div className="chart-legend"><span className="legend-block"/><span>Proporción de salidas observadas</span></div>
        </Panel>
      </div>
      <Panel title="Retención por supervisión" subtitle="Lectura exclusivamente retrospectiva. Se suprimen grupos pequeños para proteger la privacidad." className="supervisor-panel">
        {data.supervisors.length ? <div className="supervisor-list">{data.supervisors.map((s,i)=><div className="supervisor-row" key={`grupo-retrospectivo-${i}`}><div><strong>{s.suppressed ? 'Grupo suprimido' : `Grupo agregado ${String(i + 1).padStart(2,'0')}`}</strong><span>{s.suppressed ? 'Tamaño de grupo protegido' : `${number(s.sampleSize)} observaciones`}</span></div><div className="supervisor-rate">{s.suppressed ? '—' : fmtRate(s.retentionRate)}<small>retención</small></div><div className="supervisor-track"><span style={{width:`${s.suppressed ? 0 : (s.retentionRate ?? 0) * 100}%`}}/></div></div>)}</div> : <div className="empty-inline">No hay datos retrospectivos de supervisión para este corte.</div>}
        <div className="privacy-note"><ShieldCheck size={15}/> Supervisión no está disponible en la evaluación de entrevista ni debe interpretarse como una característica individual.</div>
      </Panel>
    </>}
  </div>;
}

function DiagnosticPage({ filters, setFilters }: { filters: FilterState; setFilters: (x: FilterState) => void }) {
  const params = useMemo(() => ({ campaign: filters.campaign || undefined, shift: filters.shift || undefined, supervisor: filters.supervisor || undefined, startMonth: filters.startMonth || undefined, endMonth: filters.endMonth || undefined }), [filters]);
  const { data, isLoading, error, refetch } = useGetDiagnosticAnalytics(params, { query: { queryKey: getGetDiagnosticAnalyticsQueryKey(params) } });
  const costs = useGetCostSettings({ query: { queryKey: getGetCostSettingsQueryKey() } });
  const saveCosts = useUpdateCostSettings();
  const qc = useQueryClient();
  const [editCosts, setEditCosts] = useState(false);
  return <div className="content">
    <PageTitle eyebrow="EVIDENCIA Y CONTEXTO · 03" title="¿Qué está asociado?" subtitle="Hallazgos descriptivos y límites explícitos para explicar cada cifra."/>
    <Filters filters={filters} setFilters={setFilters}/>
    <StateMessage loading={isLoading} error={error} retry={() => void refetch()}/>
    {data && <>
      <div className="finding-banner"><div className="finding-glyph"><Activity size={19}/></div><div><span>CONCLUSIÓN SOBRE PUNTAJE TÉCNICO</span><strong>{data.technicalConclusion}</strong><small>{data.technicalEvidence.method} · ρ = {fmtValue(data.technicalEvidence.correlation, 3)} · p = {fmtValue(data.technicalEvidence.pValue, 3)} · n = {number(data.technicalEvidence.sampleSize)}</small></div><span className="finding-sample">{number(data.sampleSize)} observaciones · {data.period}</span></div>
      <div className="two-col diagnostic-cols">
        <Panel title="Hallazgos principales" subtitle="Cada observación conserva su muestra y limitación.">
          <div className="finding-list">{data.findings.length ? data.findings.map((f,i)=><article className="finding-item" key={`${f.title}-${i}`}><div className="finding-head"><h3>{f.title}</h3><span>n = {number(f.sampleSize)}</span></div><p>{f.evidence}</p><div className="limitation"><span>LÍMITE</span>{f.limitation}</div><div className="recommendation"><ArrowRight size={14}/>{f.recommendation}</div></article>) : <div className="empty-inline">Sin hallazgos en este corte.</div>}</div>
        </Panel>
        <div className="stack">
          <Panel title="Bandas de puntaje técnico" subtitle="La asociación observada no implica causalidad.">
            {data.technicalBands.length ? <div className="band-list">{data.technicalBands.map((b,i)=><div className="band-row" key={`${b.band}-${i}`}><div className="band-caption"><span>{b.band}</span><strong>{fmtRate(b.rate)}</strong></div><div className="band-track"><span style={{width:`${Math.min(100,(b.rate ?? 0) * 100)}%`}}/></div><small>{number(b.events)} eventos de {number(b.sampleSize)}</small></div>)}</div> : <div className="empty-inline">Sin bandas disponibles.</div>}
          </Panel>
          <Panel title="Perfiles con mayor tasa" subtitle="Agregados; sin nombres ni documentos.">
            {data.topProfiles.length ? <div className="profile-list">{data.topProfiles.map((p,i)=><div className="profile-row" key={`${p.dimension}-${p.value}-${i}`}><span className="profile-dimension">{p.dimension}</span><span className="profile-value">{p.value}</span><span className="profile-rate">{fmtRate(p.rate)}</span><small>n={number(p.sampleSize)}</small></div>)}</div> : <div className="empty-inline">Sin perfiles disponibles.</div>}
          </Panel>
        </div>
      </div>
      <div className="two-col">
        <Panel title="Motivos de salida" subtitle={data.reasonAvailability}>
          {data.exitReasons.length ? <div className="reason-list">{data.exitReasons.map((r,i)=><div className="reason-row" key={`${r.reason}-${i}`}><span>{r.reason}</span><div className="reason-track"><span style={{width:`${Math.min(100,r.percentage * 100)}%`}}/></div><b>{fmtRate(r.percentage)}</b><small>{number(r.count)}</small></div>)}</div> : <div className="empty-inline">No hay respuestas agregadas disponibles.</div>}
        </Panel>
        <Panel title="Motivos en contexto" subtitle="Cruces descriptivos con campaña, turno y variables revisadas en el diagnóstico.">
          {data.reasonContext.length ? <div className="reason-context-list">{data.reasonContext.map((r,i)=><article className="reason-context" key={`${r.reason}-${i}`}><div className="finding-head"><h3>{r.reason}</h3><span>n = {number(r.sampleSize)}</span></div><p>Campaña: {r.topCampaign ?? 'Sin grupo suficiente'} · Turno: {r.topShift ?? 'Sin grupo suficiente'}</p><p>Supervisión: {r.topSupervisor ?? 'Sin grupo suficiente'} · Puntaje técnico medio: {r.averageTechnicalScore == null ? 'Sin muestra suficiente' : `${fmtValue(r.averageTechnicalScore, 1)} / 100`}</p><small>{r.limitation}</small></article>)}</div> : <div className="empty-inline">No hay grupos de motivos con el tamaño mínimo para mostrar contexto.</div>}
        </Panel>
        <Panel title="Costo de reemplazo" subtitle={costs.data ? `Supuestos ${costs.data.source === 'real' ? 'reales' : 'estimados'} · ${costs.data.currency}` : 'Supuestos operativos configurables'} action={costs.data && <button className="small-action" onClick={()=>setEditCosts(!editCosts)}>{editCosts ? 'Cancelar' : 'Editar supuestos'}</button>}>
          <StateMessage loading={costs.isLoading} error={costs.error} retry={()=>void costs.refetch()}/>
          {costs.data && <><div className="cost-summary"><span>Costo total estimado de las salidas tempranas</span><strong>{costs.data.currency} {number(costs.data.totalCost)}</strong><small>{number(costs.data.earlyResignations)} salidas × {costs.data.currency} {number(costs.data.replacementCost)} por reemplazo</small></div>
          {editCosts && <form className="cost-form" onSubmit={e=>{e.preventDefault(); const f=new FormData(e.currentTarget); saveCosts.mutate({data:{recruitment:Number(f.get('recruitment')),training:Number(f.get('training')),idleTime:Number(f.get('idleTime')),currency:String(f.get('currency')) as 'COP'|'USD',source:String(f.get('source')) as 'real'|'estimated'}}, {onSuccess:()=>{setEditCosts(false); void qc.invalidateQueries({queryKey:getGetCostSettingsQueryKey()})}})}}>
            {(['recruitment','training','idleTime'] as const).map(k=><label key={k}>{k==='recruitment'?'Reclutamiento':k==='training'?'Formación':'Tiempo inactivo'}<input name={k} type="number" min="0" step="1" defaultValue={costs.data[k]}/></label>)}
            <label>Moneda<select name="currency" defaultValue={costs.data.currency}><option value="COP">COP</option><option value="USD">USD</option></select></label>
            <label>Tipo de dato<select name="source" defaultValue={costs.data.source}><option value="estimated">Estimado</option><option value="real">Real</option></select></label>
            <Button type="submit" disabled={saveCosts.isPending}>{saveCosts.isPending?'Guardando…':'Guardar supuestos'}</Button>
          </form>}</>}
        </Panel>
      </div>
      <Panel title="Limitaciones del análisis" subtitle="Condiciones necesarias para interpretar con rigor.">
        <div className="limitations-grid">{data.limitations.map((l,i)=><div className="limitation-card" key={`${l}-${i}`}><span>0{i+1}</span><p>{l}</p></div>)}</div>
      </Panel>
    </>}
  </div>;
}

function CandidatePage() {
  const model = useGetModelStatus({ query: { queryKey: getGetModelStatusQueryKey() } });
  const predict = usePredictCandidateRisk();
  const [prediction, setPrediction] = useState<CandidatePrediction | null>(null);
  const initial: CandidateInput = { technicalScore: 50, priorBpoExperienceYears: 0, campaign: '', preferredShift: 'day', scheduleAvailability: 'flexible' };
  const [form, setForm] = useState<CandidateInput>(initial);
  const set = (key: keyof CandidateInput, value: string | number) => setForm(f=>({...f,[key]:value}));
  const submit = (e: React.FormEvent) => { e.preventDefault(); setPrediction(null); predict.mutate({data:form}, {onSuccess:setPrediction}); };
  return <div className="content candidate-content">
    <PageTitle eyebrow="USO RESPONSABLE · 04" title="Una señal para conversar." subtitle="Explora una estimación del modelo como apoyo contextual. Nunca es una recomendación de contratación."/>
    <div className="notice-card"><ShieldCheck size={20}/><div><b>Apoyo, no decisión</b><p>La probabilidad estimada no evalúa el valor de una persona. No uses el resultado para aprobar, descartar ni ordenar candidaturas.</p></div></div>
    <div className="candidate-layout">
      <Panel title="Contexto de evaluación" subtitle="Ingresa únicamente variables permitidas. No incluyas datos personales.">
        <StateMessage loading={model.isLoading} error={model.error} retry={()=>void model.refetch()}/>
        {model.data && !model.data.readyForPrediction && <div className="inline-warning"><AlertCircle size={17}/><span>{model.data.message || 'El modelo no está disponible para generar estimaciones.'}</span></div>}
        <form className="candidate-form" onSubmit={submit}>
          <label>Puntaje técnico <div className="input-with-unit"><input type="number" min="0" max="100" required value={form.technicalScore} onChange={e=>set('technicalScore',Number(e.target.value))}/><span>/ 100</span></div><small>Valor de evaluación técnica según la escala vigente.</small></label>
          <label>Experiencia previa en BPO <div className="input-with-unit"><input type="number" min="0" max="60" step=".1" required value={form.priorBpoExperienceYears} onChange={e=>set('priorBpoExperienceYears',Number(e.target.value))}/><span>años</span></div></label>
          <label>Campaña <input required value={form.campaign} onChange={e=>set('campaign',e.target.value)} placeholder="Nombre de campaña"/></label>
          <label>Turno preferido<select value={form.preferredShift} onChange={e=>set('preferredShift',e.target.value as CandidateInput['preferredShift'])}><option value="day">Día</option><option value="evening">Tarde</option><option value="night">Noche</option></select></label>
          <label className="full-field">Disponibilidad de horario<select value={form.scheduleAvailability} onChange={e=>set('scheduleAvailability',e.target.value as CandidateInput['scheduleAvailability'])}><option value="flexible">Flexible</option><option value="fixed">Fija</option></select></label>
          <div className="form-actions"><Button type="submit" disabled={predict.isPending || !model.data?.readyForPrediction}>{predict.isPending ? 'Calculando estimación…' : <>Calcular estimación <ArrowRight size={16}/></>}</Button><span><ShieldCheck size={14}/> Sin supervisor, nombre ni documento</span></div>
        </form>
        {predict.error && <div className="inline-error" role="alert"><AlertCircle size={16}/>{errText(predict.error)}</div>}
      </Panel>
      <div className="result-column">
        {prediction ? <PredictionResult prediction={prediction}/> : <div className="result-placeholder"><div className="placeholder-orbit"><Target size={28}/></div><span>RESULTADO DEL MODELO</span><h2>La estimación aparecerá aquí</h2><p>Se mostrará junto con sus factores, incertidumbre y versión del modelo para que puedas explicarla.</p></div>}
        {model.data && <div className="model-mini"><span>MODELO ACTIVO</span><strong>{model.data.version ?? 'Sin versión'}</strong><small>{model.data.trained ? `Entrenado ${date(model.data.trainedAt)}` : 'No entrenado'}</small></div>}
      </div>
    </div>
    {prediction && <div className="candidate-disclaimer"><AlertCircle size={16}/>{prediction.decisionNotice}</div>}
  </div>;
}
function PredictionResult({ prediction }: { prediction: CandidatePrediction }) {
  const tone = prediction.risk.toLowerCase();
  return <Panel title="Estimación individual" subtitle={`Modelo ${prediction.modelVersion} · ${date(prediction.modelDate)}`} className="prediction-panel">
    <div className="probability"><div className={`probability-ring ${tone}`}><strong>{fmtRate(prediction.probability)}</strong><span>probabilidad</span></div><div className="risk-summary"><span className="eyebrow">SEMÁFORO DE NIVEL ESTIMADO</span><strong className={`risk-name ${tone}`}>{prediction.risk}</strong><div className={`risk-traffic ${tone}`} role="img" aria-label={`Semáforo: nivel ${prediction.risk}`}><span className="traffic-light red-light"/><span className="traffic-light yellow-light"/><span className="traffic-light green-light"/></div><p>Rojo: ≥ 40% · Amarillo: 20% a 39% · Verde: &lt; 20%. Umbrales provisionales; resultado experimental no calibrado.</p></div></div>
    <div className="uncertainty"><CircleHelp size={16}/><div><b>Incertidumbre</b><span>{prediction.uncertainty}</span></div></div>
    <div className="factor-title">FACTORES QUE CONTRIBUYEN</div>
    {prediction.factors.length ? <div className="factor-list">{prediction.factors.map((f,i)=><div className="factor-row" key={`${f.factor}-${i}`}><span className={`factor-direction ${f.effect}`}>{f.effect==='increases'?<ArrowUpRight size={15}/>:<ArrowDownRight size={15}/>}</span><div><strong>{f.factor}</strong><small>{f.value}</small></div><span className="factor-contribution">{fmtSigned(f.contribution)}</span></div>)}</div>:<div className="empty-inline">El modelo no reportó factores explicativos.</div>}
    <div className="actions-note"><strong>Acciones de apoyo sugeridas</strong>{prediction.actions.length ? prediction.actions.map((a,i)=><p key={`${a}-${i}`}><CheckCircle2 size={14}/>{a}</p>) : <p>No se reportaron acciones.</p>}</div>
  </Panel>;
}

const sourceOptions = [{value:'ats',label:'ATS / contrataciones'},{value:'payroll',label:'Nómina'},{value:'performance',label:'Desempeño'},{value:'exit_surveys',label:'Encuestas de salida'}] as const;
function DataPage() {
  const qc=useQueryClient();
  const publicDemo=import.meta.env.VITE_PUBLIC_DEMO==='true';
  const status=useGetDatasetStatus({query:{queryKey:getGetDatasetStatusQueryKey()}});
  const demo=useGenerateDemoData(), upload=useUploadDataset(), saveMapping=useSaveDatasetMapping(), validate=useValidateDataset(), etl=useRunDatasetEtl();
  const [source,setSource]=useState<typeof sourceOptions[number]['value']>('ats');
  const [preview,setPreview]=useState<UploadPreview|null>(null);
  const [mapping,setMapping]=useState<Record<string,string>>({});
  const [validation,setValidation]=useState<ValidationReport|null>(null);
  const [message,setMessage]=useState('');
  const invalidate=()=>{void qc.invalidateQueries({queryKey:getGetDatasetStatusQueryKey()});void qc.invalidateQueries({queryKey:getGetAnalyticsOverviewQueryKey()});void qc.invalidateQueries({queryKey:getGetTurnoverAnalyticsQueryKey()});void qc.invalidateQueries({queryKey:getGetDiagnosticAnalyticsQueryKey()});};
  const handleFile=async(e:React.ChangeEvent<HTMLInputElement>)=>{const file=e.target.files?.[0];if(!file)return;const base64=await new Promise<string>((resolve,reject)=>{const r=new FileReader();r.onload=()=>resolve(String(r.result).split(',')[1]??'');r.onerror=()=>reject(new Error('No se pudo leer el archivo.'));r.readAsDataURL(file)});upload.mutate({data:{source,fileName:file.name,contentBase64:base64}},{onSuccess:p=>{setPreview(p);setSource(p.source as typeof source);setMapping(p.detectedMapping);setMessage(p.message);invalidate()}})};
  const actions=[{title:'Generar datos de demostración',body:'Crea un conjunto sintético reproducible para explorar el flujo.',button:'Generar datos demo',run:()=>demo.mutate(undefined,{onSuccess:()=>{setMessage('Datos sintéticos generados.');invalidate()}}),pending:demo.isPending,icon:Sparkles}];
  return <div className="content">
    <PageTitle eyebrow="FUENTES Y PROCESAMIENTO · 05" title="Datos con trazabilidad." subtitle="Importa, mapea y valida fuentes sin alterar los originales."/>
    <div className="inline-warning"><ShieldCheck size={17}/><span>{publicDemo?'Demo pública: se usan datos sintéticos. Por seguridad, la carga de archivos está deshabilitada y no ingreses datos personales.':'Los archivos se guardan localmente y sin cifrado. Esta versión no tiene inicio de sesión ni roles; en la vista previa del workspace usa datos sintéticos, no datos personales reales.'}</span></div>
    {status.isError ? <div className="api-unavailable-note"><AlertCircle size={19}/><div><strong>El servicio de datos aún no está desplegado</strong><span>La web está publicada, pero la API que recibe archivos y procesa conjuntos no está conectada en este entorno. Por eso no están disponibles la importación, la validación, los datos demo ni el análisis de esta sección.</span><small>El seguimiento ágil sí funciona y guarda sus cambios en este navegador.</small></div><button className="text-button" onClick={()=>void status.refetch()}>Reintentar</button></div> : <StateMessage loading={status.isLoading} error={undefined} retry={()=>void status.refetch()}/>}
    {status.data && <div className="data-summary"><div className="summary-copy"><div className="eyebrow">ESTADO DEL CONJUNTO</div><h2>{status.data.processed?'Listo para analizar':'Fuentes por preparar'}</h2><p>{status.data.processed?`Último procesamiento: ${date(status.data.lastUpdated)}.`:'Carga fuentes y ejecuta validación antes de procesar.'}</p></div><div className="data-counts"><div><b>{number(status.data.totalHires)}</b><span>contrataciones</span></div><div><b>{number(status.data.eligibleEmployees)}</b><span>elegibles</span></div><div><b>{number(status.data.earlyResignations)}</b><span>salidas tempranas</span></div></div></div>}
    <div className="two-col data-cols">
      <Panel title="Fuentes registradas" subtitle="Estado y volumen por sistema de origen." action={<span className="panel-count">{status.data?.sources.length ?? 0} fuentes</span>}>
        {status.data?.sources.length ? <div className="source-list">{status.data.sources.map((s,i)=><div className="source-row" key={`${s.source}-${i}`}><div className="source-icon"><FileSpreadsheet size={18}/></div><div className="source-info"><strong>{s.label}</strong><span>{s.filename ?? 'Sin archivo asociado'} · {number(s.records)} registros</span><small>{s.columns.length} columnas detectadas</small></div><span className={`source-state ${s.state.toLowerCase()}`}>{s.state}</span></div>)}</div> : <div className="empty-inline">No hay fuentes registradas.</div>}
      </Panel>
      <Panel title={publicDemo?'Carga deshabilitada en la demo pública':'Importar una fuente'} subtitle={publicDemo?'El backend público solo admite el conjunto sintético de demostración.':'Formatos CSV o XLSX. El archivo original se conserva.'}>
        <label className="source-select-label">Tipo de fuente<select value={source} onChange={e=>setSource(e.target.value as typeof source)}>{sourceOptions.map(o=><option value={o.value} key={o.value}>{o.label}</option>)}</select></label>
        <label className={`upload-drop ${publicDemo?'upload-disabled':''}`}><input type="file" accept=".csv,.xlsx" aria-label="Seleccionar archivo CSV o XLSX" disabled={publicDemo} onChange={e=>void handleFile(e)}/><div className="upload-visual"><FileSpreadsheet size={22}/></div><strong>{publicDemo?'Disponible solo en instalación privada':upload.isPending?'Importando archivo…':'Selecciona un archivo para importar'}</strong><span>CSV o XLSX · No se mostrarán filas individuales</span></label>
        {upload.error && <div className="inline-error"><AlertCircle size={16}/>{errText(upload.error)}</div>}
      </Panel>
    </div>
    {preview && <Panel title="Mapeo de columnas" subtitle={`${preview.fileName} · ${number(preview.records)} registros · asigna columnas al esquema analítico.`} className="mapping-panel">
      {message && <div className="success-note"><CheckCircle2 size={16}/>{message}</div>}
      <div className="mapping-grid">{Object.entries(mapping).map(([field,value])=><label key={field}><span>{field.replaceAll('_',' ')}</span><select value={value} onChange={e=>setMapping(m=>({...m,[field]:e.target.value}))}><option value="">Sin asignar</option>{preview.columns.map(c=><option key={c} value={c}>{c}</option>)}</select></label>)}</div>
      <div className="action-row"><Button kind="secondary" disabled={saveMapping.isPending} onClick={()=>saveMapping.mutate({data:{source,mapping}},{onSuccess:r=>{setMessage(r.message);invalidate()}})}>{saveMapping.isPending?'Guardando…':'Guardar mapeo'}</Button><Button kind="secondary" disabled={validate.isPending} onClick={()=>validate.mutate(undefined,{onSuccess:r=>{setValidation(r);invalidate()}})}>{validate.isPending?'Validando…':'Validar calidad'}</Button><Button disabled={etl.isPending} onClick={()=>etl.mutate(undefined,{onSuccess:r=>{setMessage(r.message);invalidate()}})}>{etl.isPending?'Procesando…':'Ejecutar ETL'}</Button></div>
      {saveMapping.error&&<div className="inline-error">{errText(saveMapping.error)}</div>}{validate.error&&<div className="inline-error">{errText(validate.error)}</div>}{etl.error&&<div className="inline-error">{errText(etl.error)}</div>}
    </Panel>}
    {validation && <Panel title="Resultado de validación" subtitle={validation.valid?'Validación completada sin bloqueos.':'Se detectaron condiciones para revisar.'} className="validation-panel">
      <div className="validation-stats">{[['Registros',validation.totalRecords],['Duplicados',validation.duplicateIds],['Valores faltantes',validation.missingValues],['Fechas inválidas',validation.invalidDates],['Sin correspondencia',validation.unmatchedRecords]].map(([label,val])=><div key={String(label)}><span>{label}</span><b>{number(Number(val))}</b></div>)}</div>
      {validation.issues.length>0&&<div className="issue-list">{validation.issues.map((i,n)=><div key={`${i.code}-${n}`}><span className={`severity ${i.severity.toLowerCase()}`}>{i.severity}</span><b>{i.message}</b><span>{i.source} · {number(i.count)}</span></div>)}</div>}
    </Panel>}
    <Panel title="Acciones de procesamiento" subtitle="Las operaciones reportan el resultado del servicio y actualizan las vistas relacionadas." className="etl-panel">
      <div className="etl-steps"><div><span className="step-num">01</span><b>Fuente original</b><small>Archivo preservado</small></div><ArrowRight size={15}/><div><span className="step-num">02</span><b>Validación</b><small>Calidad y coherencia</small></div><ArrowRight size={15}/><div><span className="step-num">03</span><b>ETL</b><small>Esquema analítico</small></div></div>
      <Button kind="secondary" disabled={demo.isPending || status.isError} onClick={actions[0].run}>{demo.isPending?'Generando…':'Generar datos sintéticos de demostración'}</Button>
      {demo.error&&<div className="inline-error">{errText(demo.error)}</div>}
    </Panel>
  </div>;
}

function ModelPage() {
  const qc=useQueryClient();
  const {data,isLoading,error,refetch}=useGetModelStatus({query:{queryKey:getGetModelStatusQueryKey()}});
  const fairness=useGetFairnessStatus({query:{queryKey:getGetFairnessStatusQueryKey()}});
  const train=useTrainModel();
  const [notice,setNotice]=useState('');
  return <div className="content">
    <PageTitle eyebrow="MODELO Y GOBERNANZA · 06" title="Medir antes de usar." subtitle="Métricas, umbrales y equidad visibles para sostener una conversación informada." action={<Button disabled={train.isPending} onClick={()=>train.mutate(undefined,{onSuccess:r=>{setNotice(r.message);void qc.invalidateQueries({queryKey:getGetModelStatusQueryKey()});void qc.invalidateQueries({queryKey:getGetFairnessStatusQueryKey()})}})}>{train.isPending?'Entrenando…':'Entrenar modelo'}</Button>}/>
    <StateMessage loading={isLoading} error={error} retry={()=>void refetch()}/>
    {train.error&&<div className="inline-error"><AlertCircle size={16}/>{errText(train.error)}</div>}{notice&&<div className="success-note"><CheckCircle2 size={16}/>{notice}</div>}
    {data && <>
      <div className="model-status-hero"><div className="model-symbol"><Layers3 size={23}/></div><div className="model-status-copy"><span>ESTADO DEL MODELO</span><h2>{data.trained?'Entrenamiento disponible':'Pendiente de entrenamiento'}</h2><p>{data.message}</p></div><div className="model-version"><span>VERSIÓN</span><strong>{data.version ?? '—'}</strong><small>{date(data.trainedAt)}</small></div></div>
      {data.metrics ? <><div className="metric-grid model-metrics">
        <Metric label="PRECISIÓN" value={fmt(data.metrics.accuracy == null ? null : data.metrics.accuracy*100)} detail="Aciertos totales" icon={Target}/>
        <Metric label="PRECISIÓN POSITIVA" value={fmt(data.metrics.precision == null ? null : data.metrics.precision*100)} detail="Predicciones positivas correctas" icon={Check}/>
        <Metric label="SENSIBILIDAD" value={fmt(data.metrics.recall == null ? null : data.metrics.recall*100)} detail="Eventos identificados" icon={Activity}/>
        <Metric label="ROC AUC" value={data.metrics.rocAuc?.toFixed(3) ?? '—'} detail={`Evaluación: ${number(data.metrics.testObservations)} observaciones`} icon={Gauge}/>
      </div>
      <div className="two-col">
        <Panel title="Comparación con baseline" subtitle="Referencia simple para dimensionar el valor del modelo.">
          <div className="baseline-table"><div className="baseline-header"><span>MÉTRICA</span><span>MODELO</span><span>BASELINE</span></div><div><b>Sensibilidad</b><strong>{fmt(data.metrics.recall==null?null:data.metrics.recall*100)}</strong><span>{fmt(data.metrics.baselineRecall==null?null:data.metrics.baselineRecall*100)}</span></div><div><b>Tasa de falsos positivos</b><strong>{fmt(data.metrics.falsePositiveRate==null?null:data.metrics.falsePositiveRate*100)}</strong><span>{fmt(data.metrics.baselineFalsePositiveRate==null?null:data.metrics.baselineFalsePositiveRate*100)}</span></div><div><b>F1</b><strong>{fmtValue(data.metrics.f1, 3)}</strong><span>—</span></div></div>
        </Panel>
        <Panel title="Matriz de confusión" subtitle={`Resultados sobre ${number(data.metrics.testObservations)} observaciones de prueba.`}>
          {data.metrics.confusionMatrix.length ? <div className="confusion-wrap"><div className="confusion-axis">OBSERVADO</div><div className="confusion-grid"><div className="confusion-labels"><span>Positivo</span><span>Negativo</span></div>{data.metrics.confusionMatrix.slice(0,2).map((row,i)=><div className="confusion-row" key={i}>{row.slice(0,2).map((v,j)=><div className={`confusion-cell cell-${i}-${j}`} key={j}><b>{number(v)}</b><small>{i===j?'acierto':'error'}</small></div>)}</div>)}</div><div className="confusion-foot"><span>Predicción negativa</span><span>Predicción positiva</span></div></div> : <div className="empty-inline">Sin matriz disponible.</div>}
        </Panel>
      </div></> : <div className="empty-card"><Gauge size={23}/><b>Métricas aún no disponibles</b><span>Entrena el modelo cuando las fuentes estén preparadas y procesadas.</span></div>}
      <div className="two-col">
        <Panel title="Umbrales de interpretación" subtitle="Bandas informativas; requieren revisión y calibración.">
          <div className="threshold-bands"><div className="threshold low"><span>BAJO</span><strong>&lt; {fmt(data.thresholds.low*100)}</strong></div><div className="threshold mid"><span>MEDIO</span><strong>{fmt(data.thresholds.low*100)} – {fmt(data.thresholds.high*100)}</strong></div><div className="threshold high"><span>ALTO</span><strong>≥ {fmt(data.thresholds.high*100)}</strong></div></div><div className="threshold-note"><CircleHelp size={15}/>{data.thresholds.provisional?'Umbrales provisionales: no usar para decisiones automáticas.':'Los umbrales orientan la lectura y no sustituyen criterio humano.'}</div>
        </Panel>
        <Panel title="Equidad y grupos" subtitle="La disponibilidad de grupos depende de la información autorizada.">
          <StateMessage loading={fairness.isLoading} error={fairness.error} retry={()=>void fairness.refetch()}/>
          {fairness.data&&<><div className="fairness-status"><span className={`fairness-indicator ${fairness.data.evaluated?'evaluated':''}`}/><strong>{fairness.data.status}</strong></div><p className="fairness-note">{fairness.data.note}</p><div className="group-chips">{fairness.data.groupsAvailable.length ? fairness.data.groupsAvailable.map(g=><span key={g}>{g}</span>) : <span>No hay grupos disponibles para evaluar.</span>}</div><div className="excluded"><b>Variables excluidas del modelo</b><div>{fairness.data.excludedFeatures.length?fairness.data.excludedFeatures.map(x=><span key={x}>{x}</span>):<span>No reportadas</span>}</div></div></>}
        </Panel>
      </div>
      <div className="features-grid"><Panel title="Variables consideradas" subtitle={`${number(data.observations)} observaciones · ${number(data.eventCount)} eventos`}><div className="feature-chips">{data.features.length?data.features.map(f=><span key={f}>{f}</span>):<div className="empty-inline">Sin variables reportadas.</div>}</div></Panel><Panel title="Variables excluidas" subtitle="No están disponibles para el modelo."><div className="feature-chips muted-chips">{data.excludedFeatures.length?data.excludedFeatures.map(f=><span key={f}>{f}</span>):<div className="empty-inline">Sin variables excluidas reportadas.</div>}</div></Panel></div>
    </>}
  </div>;
}

type AgileState = { name: string; days: number; points: number; completed: string; goal: number; delivered: number; defects: number; wip: number; leadHours: number; deploys: number; recoveryHours: number; changeFail: number; rework: number; objective: string; deliveredText: string; pendingText: string; lessons: string; nextSteps: string };
const agileDefaults: AgileState = { name: 'Sprint de ejemplo', days: 10, points: 34, completed: '3, 2, 4, 3, 2, 4, 1, 3, 2, 3', goal: 80, delivered: 27, defects: 2, wip: 5, leadHours: 24, deploys: 4, recoveryHours: 3, changeFail: 10, rework: 15, objective: 'Describir el objetivo del sprint', deliveredText: 'Registrar los entregables completados', pendingText: 'Registrar lo que quedó pendiente', lessons: 'Anotar aprendizajes del equipo', nextSteps: 'Definir acciones, responsables y fechas' };
function AgileProjectPage() {
  const [s, setS] = useState<AgileState>(() => { try { const v = localStorage.getItem('radar-agile-project-v1'); return v ? { ...agileDefaults, ...JSON.parse(v) } : agileDefaults; } catch { return agileDefaults; } });
  const update = (key: keyof AgileState, value: string) => { const next = { ...s, [key]: ['name','completed','objective','deliveredText','pendingText','lessons','nextSteps'].includes(key) ? value : Number(value) }; setS(next); try { localStorage.setItem('radar-agile-project-v1', JSON.stringify(next)); } catch { /* storage may be unavailable */ } };
  const completed = s.completed.split(',').map(x => Math.max(0, Number(x.trim()) || 0)).slice(0, Math.max(1, s.days));
  const chart = Array.from({ length: Math.max(1, s.days) + 1 }, (_, day) => { const done = completed.slice(0, day).reduce((a,b) => a+b, 0); return { day: `D${day}`, ideal: Math.max(0, s.points - s.points * day / Math.max(1,s.days)), actual: Math.max(0, s.points - done) }; });
  const remaining = chart.at(-1)?.actual ?? s.points;
  const saveCloseout = () => { const body = `# Documento de cierre · ${s.name}\n\nFecha: ${new Date().toLocaleDateString('es-CO')}\n\n## Objetivo\n${s.objective}\n\n## Entregables completados\n${s.deliveredText}\n\n## Pendientes\n${s.pendingText}\n\n## Burndown\nPuntos planificados: ${s.points}. Puntos restantes estimados: ${remaining}.\n\n## Indicadores de rendimiento\nCumplimiento del objetivo: ${s.goal}%. Puntos entregados: ${s.delivered}. Defectos: ${s.defects}. Trabajo en curso: ${s.wip}.\n\n## Métricas DORA\nFrecuencia de despliegue: ${s.deploys}/semana. Tiempo de entrega de cambios: ${s.leadHours} horas. Recuperación de despliegue fallido: ${s.recoveryHours} horas. Tasa de fallos de cambio: ${s.changeFail}%. Tasa de retrabajo de despliegue: ${s.rework}%.\n\n## Aprendizajes\n${s.lessons}\n\n## Próximas acciones\n${s.nextSteps}\n`; const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([body], { type: 'text/markdown;charset=utf-8' })); a.download = `cierre-${s.name.trim().replace(/[^a-z0-9]+/gi,'-').toLowerCase() || 'proyecto'}.md`; a.click(); URL.revokeObjectURL(a.href); };
  const field = (label: string, key: keyof AgileState, type = 'number', unit?: string) => <label className="agile-field"><span>{label}{unit && <small>{unit}</small>}</span><input type={type} value={s[key]} min={type === 'number' ? 0 : undefined} onChange={e => update(key,e.target.value)}/></label>;
  return <div className="content"><PageTitle eyebrow="RETROSPECTIVA DEL PROYECTO · APARTADO COMPLEMENTARIO" title="Revisar cómo trabajamos." subtitle="Un espacio de retrospectiva para registrar el avance, la entrega y los aprendizajes del equipo. Es independiente del análisis de permanencia y del modelo predictivo." action={<Button onClick={saveCloseout}>Descargar cierre</Button>}/>
    <div className="agile-notice"><ClipboardList size={17}/> Apartado complementario de retrospectiva. No forma parte de los resultados ni del funcionamiento analítico del Radar. Los cambios se guardan solo en este navegador.</div>
    <div className="agile-layout"><Panel title="Burndown del sprint" subtitle="Puntos restantes reales frente al ritmo ideal."><div className="agile-controls">{field('Nombre del sprint','name','text')}{field('Duración','days','number','días')}{field('Puntos planificados','points')}</div><label className="agile-field agile-wide"><span>Puntos completados por día <small>separados por comas</small></span><input value={s.completed} onChange={e=>update('completed',e.target.value)}/></label><div className="burndown-chart"><svg viewBox="0 0 640 240" role="img" aria-label="Gráfico de puntos pendientes por día"><line x1="45" y1="20" x2="45" y2="200"/><line x1="45" y1="200" x2="620" y2="200"/>{chart.map((p,i)=><g key={p.day}><text x={45+i*575/Math.max(1,chart.length-1)} y="222">{p.day}</text>{i>0&&<><line className="ideal-line" x1={45+(i-1)*575/Math.max(1,chart.length-1)} y1={200-(chart[i-1].ideal/Math.max(1,s.points))*170} x2={45+i*575/Math.max(1,chart.length-1)} y2={200-(p.ideal/Math.max(1,s.points))*170}/><line className="actual-line" x1={45+(i-1)*575/Math.max(1,chart.length-1)} y1={200-(chart[i-1].actual/Math.max(1,s.points))*170} x2={45+i*575/Math.max(1,chart.length-1)} y2={200-(p.actual/Math.max(1,s.points))*170}/></>}</g>)}</svg><div className="chart-legend"><span><i className="ideal-dot"/>Ideal</span><span><i className="actual-dot"/>Real</span><b>{remaining} puntos restantes</b></div></div></Panel>
    <Panel title="Indicadores de rendimiento" subtitle="Señales de flujo y entrega a nivel de equipo."><div className="agile-fields">{field('Cumplimiento del objetivo','goal','number','%')}{field('Puntos entregados','delivered')}{field('Defectos encontrados','defects')}{field('Trabajo en curso','wip')}</div><p className="agile-hint">Revisar en conjunto con calidad y contexto; no usar para comparar ni calificar personas.</p></Panel></div>
    <Panel title="Métricas DORA" subtitle="Cinco medidas para observar la entrega de software."><div className="agile-fields">{field('Frecuencia de despliegue','deploys','number','por semana')}{field('Tiempo de entrega de cambios','leadHours','number','horas')}{field('Recuperación de despliegue fallido','recoveryHours','number','horas')}{field('Tasa de fallos de cambio','changeFail','number','%')}{field('Tasa de retrabajo de despliegue','rework','number','%')}</div><p className="agile-hint">Registra periodos comparables. DORA define las métricas de entrega y confiabilidad del software.</p></Panel>
    <Panel title="Documento de cierre" subtitle="Completa los campos y descarga un archivo Markdown para compartir o archivar."><div className="agile-fields">{field('Objetivo del proyecto','objective','text')}{field('Entregables completados','deliveredText','text')}{field('Pendientes','pendingText','text')}{field('Aprendizajes','lessons','text')}{field('Próximas acciones','nextSteps','text')}</div><div className="agile-export"><span>El cierre incluye resumen, Burndown, indicadores y métricas DORA.</span><Button kind="secondary" onClick={saveCloseout}>Descargar documento de cierre</Button></div></Panel>
  </div>;
}

function Router() {
  const [location] = useLocation();
  const [filters, setFilters] = useState<FilterState>(blankFilters);
  const status=useGetDatasetStatus({query:{queryKey:getGetDatasetStatusQueryKey()}});
  const health=useHealthCheck({query:{queryKey:getHealthCheckQueryKey()}});
  const synthetic=status.data?.syntheticData ?? health.data?.syntheticData ?? false;
  return <ErrorBoundary resetKey={location}><Shell synthetic={synthetic}><Switch>
    <Route path="/" component={OverviewPage}/>
    <Route path="/retrospectiva" component={AgileProjectPage}/>
    <Route path="/proyecto" component={AgileProjectPage}/>
    <Route path="/rotacion"><TurnoverPage filters={filters} setFilters={setFilters}/></Route>
    <Route path="/diagnostico"><DiagnosticPage filters={filters} setFilters={setFilters}/></Route>
    <Route path="/candidato" component={CandidatePage}/>
    <Route path="/datos" component={DataPage}/>
    <Route path="/modelo" component={ModelPage}/>
    <Route component={NotFound}/>
  </Switch></Shell></ErrorBoundary>;
}
function App() {
  return <QueryClientProvider client={queryClient}><TooltipProvider><WouterRouter base={import.meta.env.BASE_URL.replace(/\/$/, '')}><Router/></WouterRouter><Toaster/></TooltipProvider></QueryClientProvider>;
}
export default App;
