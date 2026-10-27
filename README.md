# Radar de Permanencia — People Analytics

Aplicación local para analizar rotación voluntaria en los primeros 180 días en empresas BPO y call center. Incluye cohortes, diagnóstico, control de calidad de datos, configuración transparente de costos y un modelo experimental de regresión logística. La predicción es un apoyo para aclarar expectativas y planear acompañamiento; nunca acepta ni rechaza candidatos.

El producto consume un backend Python/FastAPI independiente. Replit solo aporta una vista previa opcional; el uso local no requiere autenticación, base de datos, servicios alojados ni llaves de API. No cargues datos reales sin autorización institucional.

## Requisitos

- Windows 10/11 de 64 bits.
- Node.js 20.19+ o 22.12+ (incluye npm).
- Python 3.11 o superior.
- PowerShell.

## Ejecutar desde una descarga limpia

Abre una ventana de PowerShell en la carpeta descargada:

```powershell
cd .\artifacts\people-analytics
npm ci
cd ..\..

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r .\backend\requirements.txt
Copy-Item .\.env.example .\.env
```

Si PowerShell bloquea la activación del entorno, ejecuta para esta ventana:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Inicia FastAPI en la primera ventana, desde la raíz del proyecto:

```powershell
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

Abre una segunda ventana de PowerShell y ejecuta el frontend:

```powershell
cd .\artifacts\people-analytics
npm run dev -- --host 127.0.0.1
```

Vite muestra la URL local, normalmente `http://localhost:5173`. FastAPI ofrece documentación local en `http://localhost:8000/people-api/docs`. El frontend lee `.env` desde la raíz; `VITE_API_URL` debe apuntar al origen del servidor FastAPI, sin añadir `/people-api`.

## Probar el flujo de demostración

1. En la aplicación, selecciona **Datos y calidad** y genera los datos sintéticos. Son datos completamente ficticios, identificados en la interfaz y en `data/sample/`.
2. Ejecuta el ETL. El resultado limpio se escribe en `data/processed/`; las fuentes originales no se sobrescriben.
3. Abre **Modelo**, entrena la regresión logística y consulta la matriz de confusión, recall, falsos positivos, baseline y ROC-AUC cuando se pueda calcular.
4. En **Semáforo del candidato**, prueba un perfil de entrevista. La respuesta usa el modelo entrenado y muestra contribuciones individuales del modelo y advertencias.
5. Cambia los filtros de período, campaña, turno o supervisor para comparar cohortes. Los activos con menos de 180 días de seguimiento y los retiros involuntarios anteriores a 180 días no se cuentan como permanencias confirmadas.

Los datos de demo se regeneran con semilla fija mediante `python -m backend.app.demo`; al usar la interfaz, el botón **Generar datos sintéticos** realiza también el procesamiento inicial.

## Fuentes CSV/XLSX

Carga por separado las fuentes de contratación (ATS) y nómina/retiros. Desempeño y encuestas de salida son opcionales. Mapea las columnas mostradas a los campos permitidos y revisa el reporte de calidad antes de ejecutar el ETL. CSV y XLSX de hasta 10 MB se guardan en `data/raw/originals/` con nombre único; se conservan como originales. Los campos fuera de la lista autorizada no entran al dataset analítico.

El dataset procesado usa identificadores seudonimizados; los dashboards y respuestas analíticas son agregados y no muestran nombres ni documentos. El almacenamiento local no cifra archivos ni reemplaza controles de acceso institucionales. Mantén el proyecto en un disco y una cuenta de usuario protegidos.

## Pruebas y comprobaciones

Desde la raíz, con el entorno virtual activo:

```powershell
python -m pytest .\backend\tests -q
python -m compileall .\backend\app
```

Para comprobar la instalación de frontend:

```powershell
cd .\artifacts\people-analytics
npm ci
npm run typecheck
npm run build
```

Los resultados efectivamente ejecutados en este entorno se documentan al cierre en `docs/traceability.md`; las instrucciones anteriores no afirman por sí mismas que Windows haya sido validado.

## Archivos y límites locales

- Fuentes sintéticas versionadas: `data/sample/`.
- Fuentes subidas, resultados procesados y configuraciones locales: `data/raw/`, `data/processed/`.
- Modelo entrenado y evaluación: `models/`.
- Contrato API: `lib/api-spec/openapi.yaml`.
- Backend: `backend/app/`.
- Frontend: `artifacts/people-analytics/`.
- Matriz de trazabilidad: `docs/traceability.md`.

`data/raw/`, `data/processed/`, `models/`, `.env` y los entornos virtuales están excluidos de Git. No se versionan datos reales ni modelos entrenados.

## Limitaciones importantes

- Los valores por defecto de costos y los umbrales de riesgo son estimaciones provisionales.
- La regresión logística solo puede entrenar si hay suficientes observaciones etiquetadas de ambas clases. Evalúa con un holdout separado y no calibra las probabilidades.
- Los datos sintéticos demuestran el flujo técnico; no describen una empresa real.
- La evaluación de equidad por grupos no está disponible sin datos de auditoría legítimos y autorizados. Excluir atributos sensibles no garantiza equidad.
- Esta versión local no proporciona inicio de sesión ni control de acceso por roles. No expone registros individuales en dashboards, pero la carpeta local de datos debe protegerse a nivel del sistema operativo.
- La documentación de privacidad en Colombia es informativa y no certifica cumplimiento de la Ley 1581 de 2012. Requiere revisión jurídica, del responsable del tratamiento y de seguridad de la organización.


## Publicación y QR

Esta descarga no trae un destino público activo ni configuración de base de datos alojada. El backend guarda archivos, estado y modelos en el sistema de archivos local; por ello, el despliegue del frontend estático por sí solo no habilita el flujo completo ni comparte datos entre visitantes.

Para publicar la demo completa se necesita desplegar el frontend y el backend Python en un servicio que permita disco persistente, configurar `VITE_API_URL` y `ALLOWED_ORIGINS` para los dominios públicos, y decidir la persistencia compartida. Supabase no está integrado en esta versión y no se deben exponer credenciales `service_role` al navegador. El enlace GitHub indicado no estuvo accesible desde el entorno durante esta ejecución.

No se generó un QR ficticio: debe codificar el dominio público después de completar y verificar el despliegue. La app no tiene autenticación y procesa información de recursos humanos; limita la demostración a datos sintéticos.
