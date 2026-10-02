# El tablero ambiental minero de Jujuy (MAIM): qué es, cómo funciona y cómo replicarlo

*Investigación con información pública · 2 de octubre de 2026*

**Cómo se hizo.** Con búsquedas web sobre fuentes públicas: sitios oficiales, prensa de gobierno,
diarios, boletines oficiales, documentos del Banco Mundial y casos equivalentes documentados.

**Límite importante.** El entorno donde se hizo el trabajo no pudo abrir el sitio del MAIM ni otras
páginas `.gob.ar`, porque un filtro de red lo impedía. Por eso:
- la descripción del MAIM sale de su propio texto indexado por los buscadores y de la prensa;
- **no se pudieron ver capturas de pantalla ni inspeccionar el código de la página.**

Lo que es inferencia está marcado como tal. Los datos que se apoyan en una sola fuente llevan la
marca *(1 fuente)*.

---

## 1. La página existe y es pública: MAIM Jujuy

**URL:** <https://maim.mineriajujuy.gob.ar/>

**MAIM** significa *Monitoreos Ambientales de la Industria Minera en Jujuy*. Es una plataforma
virtual del Ministerio de Minería de Jujuy. Ese ministerio era la Secretaría de Minería e
Hidrocarburos hasta fines de 2025, cuando la provincia la elevó a ministerio sin cambiar su
estructura operativa
([Panorama Minero](https://www.panorama-minero.com/es/news/la-provincia-de-jujuy-creo-el-ministerio-de-mineria)).

La plataforma se presentó en 2022
([Huella Minera, marzo de 2022](https://huellaminera.com/2022/03/jujuy-monitoreo-ambiental-en-empresas-para-garantizar-una-mineria-sustentable/)).
Se encuadra en la **Ley provincial 6260 de Digitalización de Procedimientos Administrativos**.

### Quién hace qué

| Actor | Qué hace en el MAIM |
|---|---|
| **Empresas mineras** | Ingresan su línea de base ambiental y cargan sus monitoreos |
| **Ministerio (ex Secretaría) de Minería** | Sistematiza la información, la controla y la pone a disposición de la sociedad |
| **Público en general** | Consulta datos históricos y mapas actualizados |

Según la propia plataforma, persigue tres objetivos:
- **participación ciudadana y transparencia;**
- **celeridad, economía y agilidad administrativa;**
- **articulación entre áreas de gobierno.**

### Qué datos maneja

**Matrices.** Agua superficial y subterránea, aire y ruido, suelo, costra salina, limnología,
flora y fauna.

**Puntos de control.** Hay más de 1.500 en la provincia
([Agroempresario](https://agroempresario.com/publicacion/115242/jujuy-preve-un-salto-en-la-actividad-minera-en-2026-con-mas-inversion-empleo-y-control-ambiental/)).
Unos 400 están en la zona de los salares de litio
([presentación Litio y Agua 2023](https://mineriajujuy.gob.ar/site/files_information/presentacion-litio-agua-2023.pdf)).

**Frecuencia.** Las campañas son como mínimo trimestrales. La prensa oficial informa que en los
pozos el nivel se registra cada 15 minutos
([prensa Jujuy](https://prensa.jujuy.gob.ar/empresas/monitoreo-ambiental-empresas-garantizar-una-mineria-sustentable-n105810)).

**Monitoreos Ambientales Participativos (MAP).**
- **Cantidad:** 69 en 2022 (casi la mitad, de litio), 80 en 2023 y unos 125 en 2024
  ([Agroempresario](https://agroempresario.com/publicacion/115242/jujuy-preve-un-salto-en-la-actividad-minera-en-2026-con-mas-inversion-empleo-y-control-ambiental/);
  [Cámara Minera de Jujuy](https://camaramineradejujuy.com.ar/monitoreos-ambientales-participativos/)).
- **Quiénes participan:** la empresa, su consultora y su laboratorio; las comunidades del área de
  influencia; la Policía Minera; y Calidad Ambiental.
- **Ejemplo:** en Exar, los MAP se hacen cuatro veces por año desde 2017.

> **No confundir con otro visor.** El CONICET (INECOA, CONICET-UNJu) desarrolló aparte un *visor
> ambiental de Jujuy* con más de 450 puntos de biota, clima e hidrografía, financiado por FONARSEC
> ([CONICET](https://salta-jujuy.conicet.gov.ar/plataforma-virtual-con-informacion-ambiental-de-jujuy/)).
> No es el MAIM.

### El ecosistema digital alrededor del MAIM

- **Trámites a Distancia (TAD) integrado a GDE**, el expediente electrónico con firma digital y
  trazabilidad. El GDE de Jujuy corre sobre AWS
  ([AWS](https://aws.amazon.com/es/blogs/aws-spanish/gobierno-de-jujuy-implemento-el-sistema-de-gestion-documental-electronica-gde-en-aws-en-8-semanas/)).
- **Expediente electrónico de Monitoreo Ambiental Participativo.**
  - Se presentó el 29/4/2026 y se lanzó oficialmente el 31/8/2026, después de un piloto con Exar.
  - En el lanzamiento se capacitó a 36 empresas
    ([El Libertario](https://ellibertario.com/2026/04/29/modernizacion-del-estado-presentaron-el-monitoreo-ambiental-participativo-con-tramite-a-distancia-100-digital/);
    [Jujuy al día](https://www.jujuyaldia.com.ar/2026/08/31/jujuy-presento-oficialmente-tramites-a-distancia-para-empresas-mineras/)).
  - **Desde el 1/9/2026 el Informe de Monitoreo Ambiental Participativo (IMAP) se presenta solo por
    TAD** (Res. Ministerial 22-M-2026, *1 fuente*).
- **Si.L.A.Mi.** (Sistema Integral de Legajo y Administración Minera): expediente minero 100 %
  digital, obligatorio desde el 2/3/2026
  ([Jujuy al día](https://www.jujuyaldia.com.ar/2026/02/24/jujuy-consolida-la-modernizacion-del-sistema-minero-con-la-digitalizacion-total-de-los-tramites/)).
- **IDEJuy.** Corre sobre GeoServer y ofrece WMS, WFS, WCS y CSW; se descarga en SHP, GeoJSON, CSV
  y KML ([IDEJuy](https://moderno.jujuy.gob.ar/idejuy-geoservicios/)).
- **Visor del catastro minero.** Permite descargar en SHP, KMZ y XLSX
  ([visor](https://www.mineriajujuy.gob.ar/visor-catastro/)).
- **EITI.** Jujuy adhirió en febrero de 2025. El quinto informe se presenta en diciembre de 2026
  ([El Tribuno de Jujuy](https://eltribunodejujuy.com/informacion-general/2026-9-24-0-0-0-jujuy-avanza-en-una-iniciativa-para-fortalecer-la-transparencia)).

---

## 2. Cómo está armado

### Lo que está confirmado

La arquitectura funcional tiene tres roles (empresa, autoridad y público) y un circuito de cuatro
pasos:

1. La empresa carga su línea de base y sus monitoreos.
2. La autoridad controla.
3. Lo controlado se publica.
4. El público lo consulta con históricos y mapas.

### Lo que no se encontró publicado

- **La tecnología del sitio:** framework, base de datos y librería de mapas.
- **Una API** de carga o de consulta.
- **Una plantilla de carga** para empresas.

Para saberlo hay que inspeccionar la página desde un navegador (ver la sección 6) o preguntar a
la Secretaría.

### El caso documentado más parecido: CyMA (Santa Cruz)

La Secretaría de Estado de Minería de Santa Cruz encargó entre 2021 y 2023 un sistema equivalente,
**CyMA** (*Sistema de Control y Monitoreo Ambiental remoto*). Lo desarrollaron MiningIDEAS y la
Universidad Nacional de San Luis (dirección de la Dra. Verónica Gil Costa) y está en uso desde 2023
([UNSL](https://noticias.unsl.edu.ar/01/06/2023/desarrollaron-un-software-para-el-control-ambiental-de-empresas-mineras/);
[MiningIDEAS](https://miningideas.com/blog/caso5.html);
[Prensa Santa Cruz](https://noticias.santacruz.gob.ar/organismos/energia/capacitan-en-digitalizacion-de-monitoreo-ambiental-minero);
[Extremo Minero](https://extremominero.com.ar/innovacion-tecnologica-y-compromiso-ambiental-una-plataforma-para-la-mineria-sostenible-en-santa-cruz/)).

Lo que hace CyMA:
- Cada empresa carga sus monitoreos de aire, agua y suelo **en el momento de obtenerlos**.
- Tiene **tableros y reportes** de tendencias, que los técnicos auditan de inmediato.
- Tiene un **sistema de alertas** que avisa los vencimientos de entrega.
- **Unifica criterios de reporte** y define estándares de medición.
- **Prioriza** los parámetros de mayor impacto.

Beneficios declarados: menos errores de carga, menos tiempo de evaluación y seguimiento de la
evolución de los parámetros.

### Del lado de las empresas

Albemarle abrió en EXPONOR 2026 una plataforma pública, **Mirador**, con datos del Salar de
Atacama: 125 pozos y 27 puntos superficiales, con niveles, caudales y química
([El Nortero](https://www.elnortero.cl/noticia/medioambiente/exponor-2026-minera-de-litio-abre-plataforma-de-monitoreo-ambiental-en-el-sala)).
Es la transparencia ejercida por la propia empresa, no por el Estado.

### Inferencia: la arquitectura típica de esta familia de sistemas

- Aplicación web con usuarios por rol (empresa, técnico de la autoridad, público).
- Base de datos con componente espacial: puntos, campañas y resultados por parámetro.
- Formularios o planillas para la carga, con un control previo.
- Un estado de revisión antes de publicar.
- Visor de mapa y series temporales.
- Descargas.

---

## 3. Salta y las demás provincias: con qué hay que poder conectarse

### Salta: lo que tu contacto describe ya tiene financiamiento

- **SIMSa** (Sistema de Información Minera de Salta)
  - Lo desarrolló la Secretaría de Minería y Energía con el Banco Mundial, alineado a EITI.
  - Tiene módulos de Impacto y Producción, Canon, Regalías y Administración.
  - **No tiene un módulo de monitoreo ambiental**
    ([salta.gob.ar](https://www.salta.gob.ar/prensa/noticias/simsa-impulsando-la-transparencia-y-desarrollo-en-la-mineria-saltenia-93275)).
- **Proyecto del Banco Mundial P510696**
  - **Monto y aprobación:** USD 100 millones. Lo aprobó el Banco Mundial el 6/7/2026 y lo autorizó
    el Senado salteño el 17/9/2026
    ([El Tribuno](https://www.eltribuno.com/salta/2026-9-18-0-0-0-la-provincia-ya-puede-tomar-deuda-por-250-millones-de-dolares)).
  - **Componente minero (unos USD 10 millones):**
    - nuevos módulos de SIMSa;
    - un flujo de evaluación de impacto ambiental *"complementado con un sistema integrado de
      control y monitoreo ambiental"*;
    - una **plataforma de interoperabilidad** entre organismos y con el Juzgado de Minas;
    - un catastro que georreferencia derechos mineros y pozos de agua
      ([documento de evaluación del proyecto](https://documents1.worldbank.org/curated/en/099061526175533352/pdf/BOSIB-12f87885-6324-4329-a46f-c19fc2d51058.pdf)).
  - **Las especificaciones técnicas no están publicadas.** En sus licitaciones se van a definir
    los formatos de intercambio, y conviene seguirlas.

### Otras jurisdicciones

- **Catamarca.** Desde el 1/9/2026 los informes de monitoreo ambiental se presentan solo por
  TAD/GDE (Res. Conjunta 1/2026, *1 fuente*,
  [abogados.com.ar](https://abogados.com.ar/mining-news-agosto-2026/40055)). Además, hay un
  anteproyecto de **Portal Digital de Transparencia Minera**.
- **Santa Cruz.** Tiene CyMA (ver arriba).
- **Nación.**
  - [SIACAM](https://www.argentina.gob.ar/economia/mineria/siacam/indicadores) publica producción,
    empleo y comercio exterior, no monitoreos.
  - [EITI Argentina](https://www.argentina.gob.ar/economia/mineria/eiti-portal-de-transparencia-de-las-industrias-extractivas).
  - datos.gob.ar corre sobre CKAN, con API de lectura
    ([Andino](https://portal-andino.datos.gob.ar/acerca/ckan)).
  - El SNIH / BDHI concentra información hídrica
    ([BDHI](https://www.argentina.gob.ar/obras-publicas/hidricas/base-de-datos-hidrologica-integrada)).
  - SEGEMAR publica geoservicios en SIGAM.
- **Mesa del Litio** (Jujuy, Salta y Catamarca). **No se encontró ningún acuerdo** sobre estándares
  de datos ni sobre una plataforma ambiental común.

### Cómo conectarse hoy a cada canal

| Canal | Cómo se conecta hoy |
|---|---|
| MAIM Jujuy | Carga web de la empresa. API: ninguna conocida |
| TAD/GDE Jujuy (IMAP) | Expediente electrónico: informe + Excel por componente + puntos en Shape y KMZ |
| TAD/GDE Catamarca | Expediente electrónico |
| SIMSa Salta | Formularios web. Interoperabilidad futura (P510696) |
| CyMA Santa Cruz | Carga en la plataforma. API: no publicada |
| IDEJuy, IDESa, SIGAM | Geoservicios OGC (WMS/WFS), solo lectura: sirven como capas base |
| datos.gob.ar | API CKAN de lectura. Se publica con paquetes de datos abiertos |

**Conclusión.** Ninguna plataforma oficial publica hoy una API de carga. Conectarse, hoy, es
**entregar exactamente el paquete que pide cada canal**. La conexión por API tiene que quedar lista
para cuando exista: Salta es la candidata más próxima.

---

## 4. Marco técnico-normativo para el motor de validación

### Leyes y decretos

- **Ley 24.585 (protección ambiental minera):**
  - el Informe de Impacto Ambiental (IIA) y la Declaración de Impacto Ambiental (DIA);
  - la actualización de la DIA como máximo cada dos años, con los resultados del monitoreo;
  - el **Anexo IV de niveles guía**: agua para bebida, vida acuática, irrigación y ganado; suelo;
    aire.

  Fuente: [Infoleg](https://servicios.infoleg.gob.ar/infolegInternet/anexos/30000-34999/30096/norma.htm).
- **Equivalencias.** Los mismos valores aparecen en el **Dec. 831/93, Anexo II**
  ([texto](https://biblioteca.afip.gob.ar/pdfp/Decreto-831-93-ANEXO-II.pdf)). Para agua de consumo,
  la referencia es el **CAA, art. 982**.
- **Jujuy: Dec. 7751-DEyP-2023**, que derogó el Dec. 5772/2010
  ([abogados.com.ar](https://abogados.com.ar/nueva-reglamentacion-ambiental-para-la-actividad-minera-en-la-provincia-de-jujuy/32482)).
  - Es el que regula el IMAP.
  - Fue objeto de un pedido de inconstitucionalidad de comunidades de Salinas Grandes y Laguna de
    Guayatayoc, presentado con el CELS
    ([CELS](https://www.cels.org.ar/web/2024/09/solicitamos-a-la-justicia-de-jujuy-que-declare-la-inconstitucionalidad-del-decreto-7751-2023/)).

### Qué pide el IMAP de Jujuy

Fuente: [requisitos del IMAP](https://mineriajujuy.gob.ar/site/requisitos-imap.php), Tabla I del
art. 97.

- **Contenido del informe:** datos de la empresa y del proyecto, resumen ejecutivo y cronograma, y
  la metodología.
- **Formato de los datos:** **resultados por parámetro y componente en Excel** y **puntos de
  monitoreo en Shape y KMZ**.
- **Firmas y habilitaciones:** firma de la empresa y de la consultora, y el certificado del
  Registro de Consultores.
- **Participación:** constancias de invitación al municipio, a los superficiarios, a Ambiente, a
  Recursos Hídricos, a Pueblos Indígenas y a la Dirección de Minería.
- **Respaldo de campo y laboratorio:** planillas de campo firmadas, **cadena de custodia**,
  protocolos de laboratorio y certificados de calibración.

Las presentaciones geográficas de la provincia usan **Gauss-Krüger POSGAR 94**
([requisitos del IIA](https://www.mineriajujuy.gob.ar/site/requisitos-iia.php)).

### Niveles guía que usa el prototipo

Todos se relevaron de **fuentes secundarias**. Antes de trabajar con datos reales hay que cotejarlos
con el Boletín Oficial.

| Parámetro | Uso | Nivel | Norma | Estado |
|---|---|---|---|---|
| Arsénico | Fuente de agua para bebida | 0,05 mg/L | Ley 24.585 T.1 · Dec. 831/93 T.1 | confirmado |
| Arsénico | Agua de consumo directo | 0,01 mg/L | CAA art. 982 | confirmado |
| Arsénico | Vida acuática | 0,05 mg/L | Ley 24.585 T.2 · Dec. 831/93 T.2 | confirmado |
| Arsénico | Irrigación / ganado | 0,1 / 0,5 mg/L | Ley 24.585 T.5 / T.6 | confirmado / a verificar |
| Boro | Vida acuática / irrigación / ganado | 0,75 / 0,5 / 5 mg/L | Dec. 831/93 T.2 / T.5 / Ley 24.585 T.6 | confirmado / confirmado / a verificar |
| Zinc | Vida acuática | 0,03 mg/L | Dec. 831/93 T.2 | confirmado |
| Cobre, plomo, cadmio | Vida acuática | **según la dureza** | Dec. 831/93 T.2 | ver `core/catalogo.py` |
| Cromo total | Vida acuática | 0,002 mg/L | Dec. 831/93 T.2 | confirmado |
| Litio | Irrigación | 2,5 mg/L | Dec. 831/93 T.5 | confirmado |
| Arsénico | Suelo agrícola / residencial / industrial | 20 / 30 / 50 mg/kg | Dec. 831/93 T.9 | confirmado |
| PM10 | Aire | **no se encontró una cifra argentina confirmada** | — | se compara solo con la línea de base |

### Tres hallazgos que cambian el diseño

1. **En la Puna, superar un nivel guía puede ser natural.** El arsénico y el boro superan varios
   niveles guía desde antes de cualquier proyecto. Un semáforo que lo pinte de rojo desinforma. Hace
   falta **comparar contra la línea de base** del punto.
2. **"No detectado" no siempre alcanza.** Si el límite de detección del laboratorio es mayor que el
   nivel guía (por ejemplo, cromo con LD 0,005 mg/L frente a 0,002 mg/L para vida acuática), el
   resultado **no permite concluir** que cumple.
3. **El cobre, el plomo y el cadmio para vida acuática dependen de la dureza** del agua, que hay que
   medir en la misma muestra.

---

## 5. ¿Se puede replicar? Sí, y conviene hacerlo del lado de la empresa

**Propuesta.** No competir con la plataforma oficial, sino **alimentarla**. La herramienta es para
la empresa (y para su consultora y su laboratorio): de **un solo origen de datos salen todas las
presentaciones**.
- Hoy, eso quiere decir el paquete para TAD/GDE, la planilla para MAIM, SIMSa o CyMA, y los datos
  abiertos.
- Mañana, una API para el sistema que financie Salta y para el que adopte cada provincia.

### Qué tendría la versión de producción

- **Datos.** PostgreSQL con PostGIS, más series continuas (TimescaleDB) para los sensores de nivel
  cada 15 minutos.
- **Modelo de datos.** Compatible con **OGC SensorThings** (puntos, series y observaciones), así
  cualquier plataforma que adopte el estándar se conecta sin traducciones.
- **Ingesta.** Planillas de laboratorio tal como llegan, más dataloggers por API.
- **Motor de reglas configurable por jurisdicción.** Niveles guía, usos, tolerancias de línea de
  base y requisitos del canal de presentación, en archivos de perfil.
- **Flujo con firma.** Pasos por rol, auditoría completa y firma digital integrable.
- **Conectores por canal.** Exportadores hoy; API mañana.
- **Portal público opcional** para la empresa, al estilo del Mirador de Albemarle.
- **Multiempresa.** Con roles para empresa, consultora, laboratorio y comunidad.

### Riesgos y cuidados

- **Sin API oficial, la última carga en MAIM, SIMSa o CyMA sigue siendo manual.** El sistema la
  reduce a subir un archivo ya validado.
- **Las normas cambian.** Los niveles guía y los requisitos del IMAP tienen que vivir en
  configuración versionada, no en el código.
- **El semáforo no es un dictamen.** Ordena y explica, pero la evaluación es de la autoridad. El
  prototipo lo refleja: nada se publica sin aprobación.
- **Confianza.** Se necesitan cadena de custodia, laboratorios acreditados, integridad de los
  archivos (hashes) y trazabilidad de cada corrección.

### Próximos pasos

1. **Validar con tu contacto en Jujuy:**
   - si el MAIM tiene plantilla de carga o importación masiva;
   - si hay API (aunque sea interna);
   - qué formato exacto piden en el IMAP.
2. **Seguir la licitación del P510696 en Salta.** Ahí se definen los formatos de interoperabilidad.
3. **Piloto con una empresa:** un proyecto y dos campañas reales.

---

## 6. Cómo completar lo que no se pudo ver

Para confirmar la tecnología y el diseño del MAIM:
- **Capturas.** De la portada, el mapa, una ficha de punto, un gráfico y la pantalla de ingreso de
  empresas.
- **Inspección desde un navegador con acceso.** En el código de la página se ven el framework y la
  librería de mapas.
- **Consulta directa.** Preguntar a la Secretaría por la plantilla de carga y por un acceso de
  prueba.
