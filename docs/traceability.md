# Matriz de trazabilidad Jira

Fuente consultada: proyecto SCRUM de Jira. La historia canónica del semáforo es HU-12 (SCRUM-21); la historia antigua SCRUM-11 está marcada como duplicada y no se implementa como una segunda función. Las 16 historias consultadas figuraban “Por hacer” en Jira. Los criterios de esta matriz consolidan el backlog adjunto y la descripción vigente de Jira.

| HU / Jira | Funcionalidad | Aceptación verificable | Frontend previsto | API / proceso | Verificación | Estado al cierre |
| --- | --- | --- | --- | --- | --- | --- |
| HU-01 / SCRUM-6 | Unificar contratación, nómina, desempeño y encuesta; calidad; originales retenidos | Cruce por ID; duplicados/fechas; faltantes documentados | Datos y calidad | `/datasets/upload`, `/mapping`, `/validate`, `/etl`; pandas; seudonimización | Prueba de carga CSV→mapeo→validación→ETL; originales retenidos | Implementada |
| HU-02 / SCRUM-7 | Definición común del evento de 180 días | Renuncia voluntaria; despido separado; censura excluida | Rotación, resumen, diagnóstico y modelo | Etiqueta común en ETL, cohortes y training | Pruebas de límites, eventos involuntarios y censura | Implementada |
| HU-03 / SCRUM-8 | Evolución de cohortes | Tasa y conteo por mes de ingreso | Rotación | `/analytics/turnover` | Agregados y filtros disponibles; no se afirma tendencia cuando no hay período comparable | Implementada |
| HU-04 / SCRUM-53 | Período crítico de antigüedad | No confundir mes de calendario con antigüedad; ocultar si muestra insuficiente | Rotación y diagnóstico | Análisis de mes de antigüedad | Resultado visible con muestra y cautela | Implementada |
| HU-05 / SCRUM-46 | Costos de rotación | Fórmula y componentes editables; supuestos visibles | Diagnóstico / costos | `/settings/costs` | Prueba de edición, persistencia y cálculo total | Implementada |
| HU-06 / SCRUM-22 | Filtros compartidos | Período, campaña, turno/supervisor; restablecer filtros | Rotación y diagnóstico | Query parameters de `/analytics/*` | Filtros y limpieza disponibles en UI y API | Implementada |
| HU-07 / SCRUM-10 | Retención por supervisor | N y tasa; umbral mínimo; privacidad y no causalidad | Rotación / diagnóstico | `/analytics/turnover`; supresión si n < 20 | Pruebas de umbral; grupos pequeños protegidos | Implementada |
| HU-08 / SCRUM-9 | Prueba técnica frente a permanencia | Rangos, n/tasas, conclusión explícita y limitación de comparabilidad | Diagnóstico | Spearman en `/analytics/diagnostic` | Evidencia estadística y umbral de efecto práctico; no confunde significancia con utilidad | Implementada |
| HU-09 / SCRUM-47 | Perfiles con mayor rotación | Top 3, muestras mínimas, variables permitidas/proxies excluidos | Diagnóstico | `/analytics/diagnostic` | Perfiles agregados y tamaño mínimo | Implementada |
| HU-10 / SCRUM-48 | Motivos de salida | Top 5, disponibilidad y contraste con otras variables | Diagnóstico | `/analytics/diagnostic` | Contexto de campaña/turno/supervisión, mínimo n=20 y limitaciones | Implementada |
| HU-11 / SCRUM-23 | Hallazgos y recomendaciones | 3–5 hallazgos con evidencia, muestra, límites y acción | Resumen y diagnóstico | `/analytics/diagnostic` | Evidencia, muestra y orientación humana visibles | Implementada |
| HU-12 / SCRUM-21 | Semáforo de reclutamiento | Campos permitidos de entrevista; pipeline real; nivel y advertencias | Candidato | `/model/predict`; pipeline scikit-learn | Prueba de entrenamiento/predicción y rechazo de campos no permitidos | Implementada para demostración |
| HU-13 / SCRUM-52 | Explicación individual | Tres factores de contribución y acciones de apoyo; no contratación automática | Candidato | Contribuciones logísticas a nivel individual | Explicaciones y advertencia de revisión humana | Implementada |
| HU-14 / SCRUM-49 | Confiabilidad | Holdout, recall, FPR, baseline y métricas; meta Sprint 0 | Modelo | `/model/status`, `/model/train` | Holdout estratificado y métricas visibles; sin meta aprobada ni calibración | Parcial |
| HU-15 / SCRUM-50 | Uso justo | Excluir sensibles/proxies; documentar variables; evaluar grupos si autorizado | Modelo y candidato | Lista permitida/excluida; `/model/fairness` | Sensibilidad excluida; auditoría grupal no ejecutada sin datos/autorización legítimos | Parcial |
| HU-16 / SCRUM-51 | Protección de datos | Agregación, seudonimización, límites de acceso y nota Ley 1581 | Todas las vistas / documentación | Almacenamiento local, respuestas agregadas y documentación | Avisos y controles de agregación; faltan autenticación, roles, cifrado local y política de retención | Parcial |

## Verificación de cierre

- Backend: `python3 -m pytest backend/tests -q` — 13 pruebas aprobadas; `python3 -m compileall -q backend/app` aprobado.
- Frontend: `npm ci`, `npm run typecheck` y `npm run build` desde `artifacts/people-analytics` aprobados.
- Vista Replit comprobada en resumen, diagnóstico, datos y modelo; API en estado saludable.
- La demostración contiene 720 filas sintéticas; 610 son elegibles y 230 tienen renuncia temprana observada. No son cifras de una empresa real.
- Las instrucciones de ejecución en Windows están documentadas, pero esta sesión no pudo ejecutarlas en una máquina Windows.
- No se cambiaron los estados de Jira; las historias deben cerrarse allí solo después de la revisión del equipo.

Las HU-14, HU-15 y HU-16 no deben considerarse listas para uso con datos reales. Véase `README.md`, `docs/data-protection.md` y `docs/architecture.md`.
