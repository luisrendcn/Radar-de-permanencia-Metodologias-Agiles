# Arquitectura

## Componentes

- **Frontend:** React, TypeScript, Vite, Recharts y Lucide React bajo `artifacts/people-analytics/`. Lee `VITE_API_URL`; sin esa variable, usa la ruta relativa `/people-api`.
- **Backend:** FastAPI independiente en `backend/app/`. Valida entradas con Pydantic y expone contrato HTTP versionable desde `lib/api-spec/openapi.yaml`.
- **Procesamiento:** pandas/NumPy leen CSV/XLSX de fuentes locales, aplican validaciones y escriben un CSV limpio en `data/processed/`.
- **Modelo:** pipeline de scikit-learn con imputación numérica/categórica, escalado numérico, one-hot encoding y regresión logística. El artefacto versionado local y metadatos de evaluación van a `models/`.
- **Persistencia:** archivos locales; SQLite y PostgreSQL no son necesarios para este MVP.

## Rutas y operación

La API usa el prefijo `/people-api` para que el servidor FastAPI pueda correr como servicio independiente de la plantilla del proyecto. El prefijo no implica dependencia de Replit. En Windows, Vite llama al host configurable `VITE_API_URL`; el backend usa `RADAR_DATA_DIR`, `RADAR_MODEL_DIR` y `ALLOWED_ORIGINS`.

Los workflows del proyecto pueden iniciar la interfaz y el backend para una vista previa. Son opcionales. La operación portátil documentada inicia ambos procesos desde terminales locales; no usa la API de plantilla de Replit, una base alojada ni autenticación propietaria.

## Flujo

1. Importar y conservar la fuente original.
2. Mapear solo columnas permitidas.
3. Validar duplicados, faltantes, cruces e incoherencias temporales.
4. Unificar fuentes por identificador en memoria; excluir columnas no autorizadas; seudonimizar identificadores; etiquetar el evento o mantenerlo indeterminado.
5. Guardar el resultado procesado localmente.
6. Calcular cohortes y diagnósticos agregados.
7. Entrenar/evaluar en un split estratificado con semilla fija.
8. Habilitar predicciones solo si el artefacto corresponde al dataset actual.

## Decisiones y restricciones

- El objetivo es una renuncia voluntaria en días 1–180. Un retiro involuntario anterior al día 180 y el seguimiento activo incompleto quedan indeterminados, no son permanencias exitosas.
- El supervisor se conserva para retrospectiva; no entra al formulario ni al modelo porque puede asignarse después de la entrevista.
- La predicción individual descompone coeficientes del pipeline para explicar la contribución modelada; no implica causalidad.
- No hay decisión automatizada de contratación.
- Sin grupos de auditoría con autorización, la evaluación de equidad por subgrupo se declara no evaluable.
- Los resultados agregados suprimen grupos de supervisor con menos de 20 casos para reducir exposición de grupos pequeños.
