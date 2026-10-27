# Diccionario de datos

## Fuentes

| Fuente | Campos analíticos permitidos | Obligatoria |
| --- | --- | --- |
| ATS / contratación | `employee_id`, `hire_date`, `campaign`, `shift`, `supervisor`, `technical_score`, `prior_bpo_experience_years`, `preferred_shift`, `schedule_availability` | Sí |
| Nómina / retiros | `employee_id`, `exit_date`, `exit_type`, `recruitment_cost`, `training_cost`, `idle_time_cost` | Sí |
| Desempeño | `employee_id`, `performance_score` | No |
| Encuestas de salida | `employee_id`, `reason` | No |

Los mapeos solo aceptan campos incluidos arriba. Las demás columnas se conservan en el original, pero no se incorporan al dataset limpio. Los nombres, documentos, edad, sexo, estado civil, estrato, dirección, barrio y otros proxies no forman parte del esquema analítico.

## Indicadores y etiquetas

| Campo | Definición |
| --- | --- |
| `early_resignation` | `1` renuncia voluntaria observada entre los días 1 y 180; `0` observación suficiente y sin renuncia voluntaria temprana; vacío = indeterminado. |
| `tenure_days` | Días desde ingreso hasta retiro o corte de observación. |
| `hire_month` | Cohorte según el mes de ingreso. |
| `employee_key` | Hash seudónimo persistido localmente. No se entrega en respuestas de dashboard. |
| `synthetic_data` | Marca de origen ficticio; se propaga a las respuestas para evitar confundir demostración con evidencia empresarial. |
| `turnoverRate` | Renuncias voluntarias tempranas divididas por casos elegibles con 180 días de seguimiento o evento temprano observado. |
| `involuntaryExits` | Retiros involuntarios dentro de los primeros 180 días, reportados aparte y excluidos como positivos y negativos del modelo. |
| `censoredEmployees` | Seguimiento insuficiente o evento indeterminado; no se imputan como permanencias. |

## Variables predictivas de entrevista

El pipeline solo recibe resultado de prueba técnica, experiencia BPO previa, campaña conocida en entrevista, turno preferido y disponibilidad horaria. No recibe supervisor, datos posteriores a la contratación, atributos protegidos, identificadores ni direcciones. El modelo usa estas mismas transformaciones al entrenar e inferir.

## Datos faltantes

Los faltantes del puntaje y experiencia se imputan con la mediana de entrenamiento; las categorías faltantes, con la categoría más frecuente. Para la etiqueta, un seguimiento menor de 180 días no se imputa: queda indeterminado. Se reportan faltantes y duplicados antes del ETL.
