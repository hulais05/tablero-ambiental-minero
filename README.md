# Tablero Ambiental Minero

**Monitoreos ambientales de la minería, de la planilla del laboratorio al dato público, y de ahí a
cada canal oficial.**

Las provincias mineras están armando tableros públicos de control ambiental:
- **Jujuy** tiene el [MAIM](https://maim.mineriajujuy.gob.ar/).
- **Santa Cruz** tiene CyMA.
- **Salta** está financiando el suyo con el Banco Mundial.

En todos el circuito es el mismo: **la empresa carga, la autoridad controla, la ciudadanía
consulta**. Este prototipo replica ese circuito del lado de la empresa y deja la salida lista para
cada plataforma oficial.

La investigación que lo sustenta está en [`INVESTIGACION.md`](INVESTIGACION.md): qué es el MAIM,
cómo funciona, qué canales oficiales existen y qué normas aplican.

---

## Sobre los datos

El tablero arranca con **datos reales**: la línea de base ambiental de **Mina de la Puna**, un
proyecto de plata y oro de la Puna entre Salta y Catamarca. Se publica sin el nombre del proyecto,
de la empresa, de los laboratorios ni de las consultoras. Incluye:
- 26 puntos de monitoreo;
- unos 500 resultados de agua, aire, ruido y suelo, de 2007 a 2025;
- el programa de monitoreo del Plan de Gestión Ambiental;
- las obligaciones de la DIA de Catamarca.

Cada resultado cita la tabla y la página de donde sale. Lo que se agregó o se corrigió al cargar
está detallado en [`datos/mina-puna/FUENTES.md`](datos/mina-puna/FUENTES.md).

Con datos reales aparece lo que un escenario inventado no muestra:
- **Boro y arsénico por encima del nivel guía en casi todos los puntos, antes de cualquier
  operación.** El tablero los clasifica como fondo natural.
- **Límites de detección que no alcanzan.** El laboratorio informa mercurio y cromo con un límite
  de detección mayor que el nivel guía para vida acuática. El resultado no prueba que cumpla, y el
  tablero lo marca como no concluyente.
- **Líneas de base cortas.** Varios puntos tienen una o dos campañas. Alcanzan para saber si una
  superación ya existía, pero no para marcar desvíos, y el tablero lo dice.

### El escenario sintético

Sigue disponible con `TABLERO_DATOS=sintetico streamlit run app.py` y es la base de las pruebas del
motor. Proyectos, empresas, comunidades, laboratorios y valores son ficticios. Las coordenadas caen
en la Puna, pero no corresponden a ningún proyecto real. Lo realista son los órdenes de magnitud y
los fenómenos que un tablero tiene que saber mostrar:
- arsénico y boro naturales por encima del nivel guía;
- un nivel freático que baja desde que empieza el bombeo;
- picos de material particulado en temporada de viento;
- un metal que sube aguas abajo de un dique de colas y baja con la medida correctiva;
- un laboratorio cuyo límite de detección no alcanza para evaluar.

**Niveles guía.** Se relevaron de fuentes secundarias (Ley 24.585 Anexo IV, Dec. 831/93 Anexo II,
CAA art. 982). A eso se suman los que aplica el Informe de Impacto Ambiental de la línea de base
real: aire (Tabla 8), agua (Tablas 2 y 6), suelo de uso industrial y ruido. Cada valor lleva su
norma y su estado de verificación en `core/catalogo.py`. Antes de usarlos para decidir hay que
cotejarlos con el Boletín Oficial.

**Agregar otro proyecto real** es agregar una carpeta en `datos/` con el mismo formato:
- `proyecto.json`
- `puntos.csv`
- `campanias.csv`
- `resultados.csv`
- opcionales: `componentes.csv`, `contornos.csv`, `programa.csv` y `obligaciones.csv`

`TABLERO_DATOS=<carpeta>` elige cuál se muestra.

---

## Cómo correrlo

```bash
git clone https://github.com/hulais05/tablero-ambiental-minero.git
cd tablero-ambiental-minero
pip install -r requirements.txt
streamlit run app.py
```

Se abre en `http://localhost:8501`. No necesita base de datos ni credenciales. El mapa base
(Carto) se descarga de internet; sin conexión, los puntos se ven igual sobre fondo liso.

Tests:

```bash
pip install pytest pyproj   # pyproj es opcional: verifica la proyección Gauss-Krüger
python -m pytest
```

---

## Las vistas

| Pestaña | Quién | Qué hace |
|---|---|---|
| 🌎 **Ciudadanía** | Público | Mapa, estado de cada punto, serie histórica contra el nivel guía y la línea de base, datos abiertos. **Solo lo aprobado.** |
| 🏭 **Empresa** | Responsable ambiental | Sube la planilla del laboratorio, corrige lo que el sistema marca, justifica las superaciones y presenta |
| 📋 **Cumplimiento** | Empresa | Condiciones de la DIA con su plazo, y el programa de monitoreo del PGA con el último dato cargado. Solo con datos reales |
| 🏛️ **Autoridad** | Técnico de control | Vencimientos por proyecto, revisión de lo presentado, aprobación u observación con firma |
| 🔌 **Conectores** | Empresa | La misma campaña en el formato de cada canal oficial |
| 📚 **Cómo funciona** | Todos | Qué replica, qué es real y qué no |

## El recorrido de una campaña

| Etapa | Qué pasa | Quién interviene |
|---|---|---|
| 1 · Carga | La planilla tal como la entrega el laboratorio (Excel de varias hojas o CSV) | Empresa |
| 2 · Lectura | Reconoce las columnas por sinónimo, saca la unidad del encabezado, entiende la coma decimal y «<0,005» | Sistema |
| 3 · Control de carga | Puntos no registrados, unidades que no corresponden a la matriz, valores mil veces corridos (con la corrección sugerida), duplicados, fechas futuras | Sistema |
| 4 · Semáforo | Compara contra el nivel guía del uso del punto y contra su línea de base | Sistema |
| 5 · Justificación | Toda superación del nivel guía llega explicada, o no se puede presentar | Empresa |
| 6 · Presentación | Queda firmada en el historial | Empresa |
| **7 · Revisión** | **Aprueba u observa. Nada se publica sin este paso** | **Autoridad** |
| 8 · Publicación | Pasa a la vista pública y a los datos abiertos | Sistema |

## El semáforo tiene seis estados, no tres

| Estado | Cuándo |
|---|---|
| ▲ **Supera nivel guía** | Supera el nivel guía del uso del punto y no se explica por la línea de base |
| ◆ **Atención** | Está al 80 % o más del nivel guía (en escalas lineales), o fuera del rango de la línea de base (con al menos tres campañas) |
| ✚ **No concluyente** | El límite de detección del laboratorio es mayor que el nivel guía, o falta la dureza para elegir el nivel |
| ■ **Fondo natural** | Supera el nivel guía, pero no está peor que antes del proyecto: la línea de base ya lo superaba |
| ● **Cumple** | Dentro del nivel guía y de la línea de base |
| ○ **Sin referencia** | Sin nivel guía ni línea de base con qué comparar |

En la Puna, un semáforo de tres colores pinta de rojo el arsénico natural de una laguna, y eso
desinforma. El color nunca va solo. Cada estado lleva además:
- una forma en los gráficos;
- un ícono y su nombre en las tablas;
- un tamaño en el mapa.

Así se lee también con daltonismo: el par verde-rojo se confunde en la deuteranopía.

## Conectores: un origen, todas las salidas

Hoy ninguna plataforma provincial publica una API de carga. Por eso el sistema arma exactamente lo
que pide cada canal y deja escrita la conexión por API para cuando exista.

| Salida | Para qué canal |
|---|---|
| **Paquete para expediente** (.zip) | TAD/GDE de Jujuy (IMAP) y de Catamarca. Incluye: nota, informe, Excel por componente, puntos en Shape y KMZ, una guía (`LEAME`) con lo que la empresa adjunta aparte y un manifiesto SHA-256 |
| Informe de monitoreo (HTML para imprimir a PDF) | Tiene la estructura del IMAP: empresa, resumen ejecutivo, metodología, participación, resultados por componente, justificaciones y anexos |
| Resultados por componente (.xlsx) | Una hoja por matriz, más el semáforo y los metadatos. Sirve para el MAIM, SIMSa y CyMA |
| Puntos de monitoreo en Shape | **Gauss-Krüger POSGAR 94**, con la faja que corresponda y su `.prj`. Verificado contra PROJ al centímetro |
| Puntos de monitoreo en KMZ | Coloreados por estado |
| GeoJSON | Visores web |
| **OGC SensorThings** (.json) | El estándar abierto para observaciones ambientales. Es la forma del envío por API |
| Datos abiertos Frictionless (.zip) | CSV con esquema, publicable en cualquier portal CKAN (datos.gob.ar) |

**Agregar una provincia es agregar un archivo en `perfiles/`, no tocar código.** Cada perfil
declara:
- sus canales y de qué tipo es cada uno (expediente, plataforma web, API, geoservicio, datos
  abiertos);
- qué entregables pide cada canal y qué anexos tiene que adjuntar la empresa;
- lo que queda a confirmar, y las fuentes.

El canal por API toma la URL del perfil. El token lo lee de una variable de entorno y nunca se
guarda en el repositorio.

---

## Estructura

```
app.py                  Interfaz: ciudadanía, empresa, autoridad, conectores, cómo funciona
core/catalogo.py        Matrices, parámetros, sinónimos, unidades, usos y niveles guía con su norma
core/datos.py           Escenario sintético, planilla de laboratorio de ejemplo e ingesta
core/escenario.py       Elige y carga los datos: reales (datos/) o sintéticos
datos/mina-puna/        Línea de base real, programa del PGA y obligaciones, con sus fuentes
core/validacion.py      Línea de base, semáforo de seis estados y control de carga
core/flujo.py           Estados de la campaña, quién puede hacer cada paso, historial
core/conectores.py      Exportadores por canal, Gauss-Krüger, SensorThings y envío por API
perfiles/*.json         Jujuy, Salta, Catamarca, Santa Cruz, Nación y estándares abiertos
tests/                  Ingesta, validación, flujo, conectores y recorrido completo de la app
INVESTIGACION.md        La investigación, con fuentes
```

## Alcance y límites

**Dentro del alcance:** el circuito completo de una campaña de monitoreo, de la planilla a la
publicación, y su salida a los canales oficiales que existen hoy.

**Fuera del alcance, declarado:**
- No se conecta a ningún sistema oficial: no hay APIs públicas de carga.
- No tiene base de datos persistente: el estado vive en la sesión.
- No incluye usuarios, contraseñas ni firma digital: la firma es el nombre de quien da cada paso.
- No trata series continuas de sensores (los niveles cada 15 minutos).
- No evalúa flora, fauna ni limnología: no tienen niveles guía numéricos.

Sobre el motor: acierta los fenómenos sembrados en el escenario sintético, **y eso no es un
resultado**. Los datos se generaron sabiendo qué tenía que encontrar. Es verificación del
circuito, no medición de calidad. Los datos reales sirven para ver cómo se comporta con una línea
de base de verdad: irregular, con huecos y con campañas que cubren solo parte de la red.
