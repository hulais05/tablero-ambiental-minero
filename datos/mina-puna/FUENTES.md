# Mina de la Puna: de dónde sale cada dato

Datos reales de línea de base de un proyecto de plata y oro de la Puna, en el límite entre Salta y
Catamarca. Se publican sin el nombre del proyecto, de la empresa, de los laboratorios ni de las
consultoras. Las coordenadas, los valores y las fechas son los de las fuentes.

## Fuentes

| Fuente | Qué aporta |
|---|---|
| Informe de Impacto Ambiental (IIA) de explotación, presentado en Salta (ago-2024), capítulo 2a (medio físico) y anexos 2 y 3 | Campaña de línea de base de septiembre de 2022: agua superficial, aire, ruido y suelo. Monitoreo participativo de febrero de 2024. Pozo de abastecimiento, de febrero a junio de 2024. |
| El mismo IIA, Plan de Gestión Ambiental (PGA) | Programa de monitoreo: puntos, parámetros, frecuencias y niveles de referencia. |
| Ampliación del IIA presentada en Salta (may-2025) | Ubicación aproximada de las instalaciones. |
| Respuesta a las observaciones de Catamarca (sep-2025) y sus anexos | Informes de laboratorio del monitoreo mensual de agua superficial de 2025. Pozos exploratorios de 2007. Coordenadas corregidas. |
| DIA de explotación de Catamarca (2026), extracto publicado en el Boletín Oficial | Obligaciones de la pestaña Cumplimiento. |

Cada fila de `resultados.csv` lleva en `fuente` el documento, la página y la tabla de donde sale.
`valor_original` y `unidad_original` conservan lo que está impreso; `valor` y `unidad` son lo mismo,
llevado a la unidad con la que el tablero compara.

## Qué se cargó y qué no

- **Agua:** se cargan los resultados totales. Las fracciones disueltas, la microbiología, los gases
  disueltos y la isotopía quedan afuera.
- **Agua superficial 2025:** se usan los valores de los informes de laboratorio firmados. La
  respuesta a observaciones los resume con algunos errores de copia.
- **Sin fecha, sin serie:** los resultados que la fuente no fecha quedan afuera. Es el caso de las
  mediciones in situ del primer semestre de 2025, de los niveles freáticos de 2021 y 2025 y de
  la muestra de 2021 en la toma de agua.
- **Pozos colapsados:** los pozos exploratorios 1, 3, 4 y 5 están colapsados según la respuesta de
  2025. Su serie termina en 2007.
- **Aire, ruido y suelo:** solo hay mediciones en septiembre de 2022 y en febrero de 2024. Casi
  todo da por debajo del límite de detección.

## Decisiones tomadas al cargar, a la vista

| Dónde | Qué dice la fuente | Qué se cargó |
|---|---|---|
| Pozo de abastecimiento, feb a jun de 2024 | Solo el mes | El día 15. Febrero va el 22, el día del monitoreo participativo. |
| Suelos, sep-2022 | «Septiembre de 2022» | El 29/09/2022, en medio de la campaña de campo |
| Aire, monitoreo participativo 2024 | Longitud 66°18', 50 km al este del resto de la red | 66°48'53,30", la de la respuesta de 2025, que a su vez imprime «6°48'» |
| Pozo exploratorio 4, 2007 | Segunda fila «Magnesio < 0,02» | Manganeso, como dice el protocolo de laboratorio |
| Pozo exploratorio 5, 2007 | Arsénico «0,02 µg/L» | Se omite: la unidad no se puede verificar |
| Sólidos disueltos, sep-2022 | Valor de campo y valor de laboratorio a 180 °C | El de laboratorio |

## Uso del recurso para comparar

Cada punto se compara con una sola tabla de niveles guía de la Ley 24.585, Anexo IV:

- **Cursos de agua, vegas y laguna:** vida acuática (Tabla 2).
- **Pozos:** bebida de ganado (Tabla 6), que es el criterio del PGA.
- **Aire:** Tabla 8.
- **Suelo:** uso industrial.
- **Ruido:** la guía del Banco Mundial para áreas industriales (70 dBA, diurno).

El IIA compara además el agua con las Tablas 1, 5 y 6. Los valores cargados son los que el IIA
transcribe. Hay un caso dudoso: el zinc para ganado aparece con dos unidades distintas y no se
cargó.

## Conclusiones del propio IIA

- **Agua superficial** (cap. 2a, p. 100-102): el boro supera el nivel guía en todos los sitios
  muestreados, y el informe lo atribuye a la litología volcánica de la zona. Dice lo mismo del
  arsénico. Cita textual: «el agua de la Puna es escasa y frecuentemente contiene elementos en su
  composición (de manera natural) que la condiciona para los diferentes usos».
- **Agua subterránea** (p. 103-104 y 120-123): el informe señala anomalías regionales de arsénico y
  boro de origen natural. Sobre el pozo de abastecimiento concluye que el agua no es apta para
  consumo humano ni animal sin tratamiento previo.
- **Aire, ruido y suelo** (p. 64-77 y 152-153): todo da por debajo de los niveles guía. El ruido se
  califica «no molesto» según la norma IRAM 4062.

## Observaciones de la autoridad sobre esta línea de base

En su evaluación técnica de febrero de 2025, el Ministerio de Minería de Catamarca pidió ampliar el
muestreo de agua a un ciclo hidrológico completo. Recomendó establecer «un programa de monitoreo de
agua superficial» con estadísticas por estación. El tablero lo refleja: con menos de tres campañas,
la línea de base de un punto sirve para saber si una superación ya existía, pero no para marcar
desvíos.
