#!/usr/bin/env python3
"""Construye artefactos LaTeX y gráficos descriptivos de respuestas de Google Forms.
Entrada: CSV exportado por Google Forms con el mismo orden de preguntas.
No publica respuestas individuales ni sellos de tiempo en los entregables.
"""
import csv, sys, re, shutil, textwrap, collections, datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

ROOT = Path(__file__).resolve().parent
if ROOT.name == 'scripts': ROOT = ROOT.parent
DEFAULT_CSV = ROOT/'Formulario sin título.csv'
CSV = Path(sys.argv[1]) if len(sys.argv)>1 else DEFAULT_CSV
OUT = Path(sys.argv[2]) if len(sys.argv)>2 else ROOT/'MarketLens_Encuesta_61'
OUT.mkdir(exist_ok=True,parents=True)
GRAPHS = OUT/'figuras'/'marketlens'/'encuesta'; GRAPHS.mkdir(exist_ok=True,parents=True)
(OUT/'capitulos').mkdir(parents=True,exist_ok=True)
(OUT/'apendices').mkdir(parents=True,exist_ok=True)
(OUT/'datos_agregados').mkdir(parents=True,exist_ok=True)
(OUT/'scripts').mkdir(parents=True,exist_ok=True)

with CSV.open(encoding='utf-8-sig',newline='') as f:
    reader=csv.reader(f)
    header=next(reader)
    rows=[row for row in reader if any(x.strip() for x in row)]
if len(header)!=12: raise ValueError(f'Se esperaban 12 columnas; hay {len(header)}.')
N=len(rows)
MONTHS=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
dates=sorted(datetime.date.fromisoformat(r[0][:10].replace('/', '-')) for r in rows)
start_date,end_date=dates[0],dates[-1]
cutstamp=end_date.strftime('%d/%m/%Y')
if start_date.year == end_date.year and start_date.month == end_date.month:
    period_label=f'{start_date.day} y el {end_date.day} de {MONTHS[end_date.month-1]} de {end_date.year}'
else:
    period_label=f'{start_date.day} de {MONTHS[start_date.month-1]} de {start_date.year} y el {end_date.day} de {MONTHS[end_date.month-1]} de {end_date.year}'
if any(len(row)!=12 for row in rows): raise ValueError('Filas con cantidad inesperada de columnas')
if any(not val.strip() for row in rows for val in row):raise ValueError('Hay valores vacíos; revisar antes de generar resultados')
questions=[x.replace('\n',' ').strip() for x in header[1:]]
multiselect={2,3,7,10,11} # 1-based
counts={}
for q in range(1,12):
    vals=[row[q].strip() for row in rows]
    if q in multiselect:
        counts[q]=collections.Counter(y.strip() for x in vals for y in x.split(';') if y.strip())
    else: counts[q]=collections.Counter(vals)

def short(s):
    v=s.strip().rstrip('.')
    v=v.replace('12 verces o más','12 veces o más')
    # Only display labels are normalized, counts stay on source values.
    if v=='No estoy seguro': v='No estoy seguro/a'
    return v

LABELS={
1:{'Una o dos veces':'1–2 compras','Entre 3 y 5 veces':'3–5 compras','Entre 6 y 11 veces':'6–11 compras','12 verces o más':'12 o más compras'},
2:{'Facebook Marketplace':'Facebook Marketplace','Otras plataformas de compraventa':'Otras plataformas'},
3:{'Reputación o calificaciones del vendedor':'Reputación del vendedor','Opiniones de compradores anteriores':'Opiniones de compradores','Cantidad de ventas realizadas por el vendedor':'Cantidad de ventas','Fotografías y descripción del producto':'Fotos y descripción','Precio del producto en comparación con otras publicaciones':'Comparación de precios','Métodos de pago y políticas de protección al comprador':'Pagos y protección al comprador','No suelo verificar información adicional':'No verifica información adicional'},
4:{'No suelo consultar publicaciones en marketplaces':'No consulta publicaciones'},
5:{'Nunca consideré realizar una compra en estas plataformas':'Nunca consideró comprar'},
7:{'Precio considerablemente inferior al de publicaciones similares.':'Precio muy inferior al mercado','Ausencia de calificaciones u opiniones':'Ausencia de calificaciones','Solicitud de realizar pagos fuera de la plataforma':'Pago fuera de la plataforma','Vendedor con pocas ventas registradas.':'Vendedor con pocas ventas','Información contradictoria o poco clara sobre el producto':'Información contradictoria','Fotografías o descripciones insuficientes':'Fotos o descripciones insuficientes','Ninguna de las anteriores':'Ninguna'},
9:{'Sí, probablemente la utilizaría con frecuencia.':'Sí, frecuentemente','Sí, pero solamente ante publicaciones que me generen dudas':'Sí, ante publicaciones dudosas','Probablemente no la utilizaría':'Probablemente no','No estoy seguro/a':'No estoy seguro/a'},
10:{'Información sobre el historial comercial del vendedor':'Historial comercial del vendedor','Advertencias sobre información insuficiente o no disponible':'Advertencias por información insuficiente','Explicación de los factores que generan riesgo':'Explicación de factores de riesgo','Comparación automática de precios de productos similares':'Comparación de precios','Consulta de reportes realizados por otros usuarios':'Reportes de otros usuarios','Análisis de publicaciones de diferentes marketplaces':'Análisis de varios marketplaces','Ninguna de las anteriores':'Ninguna'},
11:{'Que recopile datos personales innecesarios':'Recopilación innecesaria de datos','Que utilice información desactualizada':'Información desactualizada','Que genere advertencias incorrectas':'Advertencias incorrectas','Que requiera demasiado tiempo o esfuerzo':'Demasiado tiempo o esfuerzo','Que no sea compatible con las plataformas que utilizo':'Falta de compatibilidad','Que sus resultados sean difíciles de interpretar':'Resultados difíciles de interpretar','No tendría preocupaciones particulares':'Sin preocupaciones particulares'}
}
GRAPH_TITLES={
1:'Frecuencia de compras (últimos 12 meses)',
2:'Marketplaces utilizados',
3:'Información consultada antes de comprar',
4:'Publicaciones consideradas sospechosas',
5:'Compras desistidas por desconfianza',
6:'Confianza en mecanismos actuales (1–5)',
7:'Señales que generan mayor desconfianza',
8:'Utilidad potencial de la herramienta (1–5)',
9:'Intención declarada de uso',
10:'Funcionalidades más valoradas',
11:'Principales preocupaciones'
}
GRAPH_CAPTIONS={
1:'Frecuencia de compra declarada en marketplaces durante los últimos doce meses',
2:'Plataformas utilizadas por los encuestados durante los últimos doce meses',
3:'Información habitualmente consultada para evaluar publicaciones o vendedores',
4:'Encuestados que identificaron publicaciones potencialmente sospechosas',
5:'Encuestados que desistieron de una compra por desconfianza',
6:'Confianza declarada en los mecanismos actuales de seguridad y reputación',
7:'Características de publicaciones que generan mayor desconfianza',
8:'Utilidad potencial atribuida a una herramienta de análisis preventivo',
9:'Intención declarada de utilización de una herramienta gratuita como la propuesta',
10:'Funcionalidades prioritarias para una herramienta de análisis preventivo',
11:'Principales preocupaciones respecto del uso de la herramienta'
}

SINGLE_ORDER={
1:['Nunca','Una o dos veces','Entre 3 y 5 veces','Entre 6 y 11 veces','12 verces o más'],
4:['Sí','No','No estoy seguro','No suelo consultar publicaciones en marketplaces'],
5:['Sí','No','No lo recuerdo','Nunca consideré realizar una compra en estas plataformas'],
9:['Sí, probablemente la utilizaría con frecuencia.','Sí, pero solamente ante publicaciones que me generen dudas','No estoy seguro/a','Probablemente no la utilizaría']
}
COL='#285678'; FOCUS='#1F7D85'; GREY='#A7B6C5'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'savefig.facecolor':'white'})

for q in range(1,12):
    data=counts[q]
    if q in (6,8):
        xx=list(range(1,6)); yy=[data.get(str(x),0) for x in xx]
        fig,ax=plt.subplots(figsize=(7.6,3.3))
        bars=ax.bar(xx,yy,width=.63,color=[COL if x<=3 else FOCUS for x in xx],zorder=3)
        ax.set_xticks(xx);ax.set_xticklabels([str(x) for x in xx]);ax.set_ylabel('Respuestas');ax.set_xlabel('Valoración')
        ax.yaxis.set_major_locator(MaxNLocator(integer=True));ax.set_ylim(0,max(yy)*1.20+1)
        ax.grid(axis='y',color='#e9edf1',zorder=0)
        for b,y in zip(bars,yy): ax.text(b.get_x()+b.get_width()/2,y+max(yy)*.04,f'{y} ({y/N*100:.1f} %)'.replace('.',','),ha='center',va='bottom',fontsize=9)
        fig.subplots_adjust(left=.10,right=.97,top=.84,bottom=.22)
    else:
        order=([x for x in SINGLE_ORDER[q] if x in data] if q in SINGLE_ORDER else [x for x,_ in data.most_common()])
        vals=[data[x] for x in order]
        raw_labels=[LABELS.get(q,{}).get(x,short(x)) for x in order]
        labels=['\n'.join(textwrap.wrap(s,width=33,break_long_words=False)) for s in raw_labels]
        fig_height=max(2.55,1.04+len(vals)*.45 + sum(t.count('\n') for t in labels)*.08)
        fig,ax=plt.subplots(figsize=(8.0,fig_height))
        pos=list(range(len(vals)))
        colors=[FOCUS if (q==9 and i<2) else COL for i,_ in enumerate(vals)]
        bars=ax.barh(pos,vals,height=.62,color=colors,zorder=3)
        ax.invert_yaxis();ax.set_yticks(pos);ax.set_yticklabels(labels,fontsize=9)
        ax.set_xlim(0,max(vals)*1.30+1)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=6,integer=True))
        ax.set_xlabel('Cantidad de participantes',fontsize=9)
        ax.grid(axis='x',color='#e9edf1',zorder=0)
        ax.tick_params(axis='y',length=0)
        for b,y in zip(bars,vals):
            ax.text(y+.55,b.get_y()+b.get_height()/2,f'{y} ({y/N*100:.1f} %)'.replace('.',','),va='center',fontsize=9)
        fig.subplots_adjust(left=.45,right=.97,top=.88,bottom=.15)
    fig.text(.5,.985,GRAPH_TITLES[q],ha='center',va='top',fontsize=11,weight='bold',color='#182e43')
    foot=f'{N} respuestas | ' + ('Selección múltiple: porcentajes por participante' if q in multiselect else 'Una respuesta por participante')
    fig.text(.5,.016,foot,ha='center',va='bottom',fontsize=8,color='#536575')
    fig.savefig(GRAPHS/f'pregunta_{q:02d}.png',dpi=200,facecolor='white')
    plt.close(fig)

# Data summaries only, no individual-level record or timestamps.
with (OUT/'datos_agregados'/'frecuencias_encuesta.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['pregunta','texto_pregunta','tipo','opcion_original','etiqueta_grafico','respuestas','base','porcentaje_sobre_base'])
    for q in range(1,12):
        keys=[x for x,_ in counts[q].most_common()]
        for x in keys:
            w.writerow([q,questions[q-1],'selección múltiple' if q in multiselect else 'opción única o escala',x,LABELS.get(q,{}).get(x,short(x)),counts[q][x],N,round(100*counts[q][x]/N,4)])

n=lambda q,key:counts[q].get(key,0)
pct=lambda k:f'{100*k/N:.1f}'.replace('.',',')
esc=lambda s: (str(s).replace('\\','\\textbackslash{}').replace('&','\\&').replace('%','\\%').replace('#','\\#').replace('_','\\_').replace('$','\\$'))
q4=n(4,'Sí');q5=n(5,'Sí');q8=n(8,'4')+n(8,'5');q9=n(9,'Sí, probablemente la utilizaría con frecuencia.')+n(9,'Sí, pero solamente ante publicaciones que me generen dudas');q6high=n(6,'4')+n(6,'5')

BODY = rf'''%!TEX root = ../main.tex
% Generado del archivo CSV de Google Forms. Corte: {cutstamp}.
% Insertar desde capitulos/07-resultados.tex mediante \input{{capitulos/07-resultados-encuesta}}

\section{{Resultados de la encuesta exploratoria}}
\label{{sec:ml-resultados-encuesta}}

Con el propósito de explorar las percepciones de los compradores sobre la seguridad en plataformas digitales y el interés por herramientas preventivas, se aplicó un cuestionario de once preguntas cerradas. El corte de resultados analizado comprende \textbf{{{N} respuestas}} registradas entre el \textbf{{{period_label}}}. El instrumento, sus opciones y las condiciones del relevamiento se incluyen en el apéndice~\ref{{apx:encuesta}}; el procedimiento se describe en la sección~\ref{{subsec:ml-encuesta-metodo}}.

La encuesta se difundió mediante contactos del autor y constituye un \textbf{{relevamiento exploratorio no probabilístico}}. Las cifras expresan percepciones e intenciones declaradas del grupo consultado, sin representatividad estadística de la población general ni evidencia directa de eficacia del motor de detección de fraudes. Las preguntas de selección múltiple admitieron varias alternativas; sus porcentajes se calcularon sobre los {N} participantes y pueden sumar más del 100\,\%.

\begin{{table}}[H]
\centering
\caption{{Síntesis de resultados de la encuesta exploratoria (n={N})}}
\label{{tab:ml-encuesta-principales}}
\small
\begin{{tabularx}}{{\textwidth}}{{L r r}}
\toprule
\tb{{Indicador declarado}} & \tb{{Respuestas}} & \tb{{Porcentaje}} \\
\midrule
Encontró alguna publicación sospechosa & {q4}/{N} & {pct(q4)}\,\% \\
Desistió de una compra por desconfianza & {q5}/{N} & {pct(q5)}\,\% \\
Calificó la utilidad potencial con 4 o 5 (escala de 1 a 5) & {q8}/{N} & {pct(q8)}\,\% \\
Consideraría utilizarla de forma frecuente o ante dudas & {q9}/{N} & {pct(q9)}\,\% \\
Asignó 4 o 5 de confianza a los mecanismos actuales & {q6high}/{N} & {pct(q6high)}\,\% \\
\bottomrule
\end{{tabularx}}
\end{{table}}

\subsection{{Experiencia de compra y criterios de evaluación}}

El cuestionario contempló tanto participantes que habían comprado durante los últimos doce meses como otros que no lo habían hecho. El uso de cada plataforma, que podía informarse en conjunto con otras, se presenta en la figura~\ref{{fig:ml-encuesta-02}}. Mercado Libre fue seleccionado por \textbf{{{n(2,'Mercado Libre')} personas ({pct(n(2,'Mercado Libre'))}\,\%)}}. En cuanto a los criterios consultados, los más frecuentes fueron la reputación o calificaciones del vendedor (\textbf{{{n(3,'Reputación o calificaciones del vendedor')}/{N}}}) y las opiniones de compradores anteriores (\textbf{{{n(3,'Opiniones de compradores anteriores')}/{N}}}), tal como muestra la figura~\ref{{fig:ml-encuesta-03}}.

\subsection{{Percepción de riesgo y confianza}}

\textbf{{{q4} participantes ({pct(q4)}\,\%)}} señalaron haber encontrado alguna publicación potencialmente sospechosa (figura~\ref{{fig:ml-encuesta-04}}), mientras que \textbf{{{q5} ({pct(q5)}\,\%)}} indicaron haber desistido de una compra por desconfianza (figura~\ref{{fig:ml-encuesta-05}}). Ambas preguntas recogen experiencias autopercibidas: no identifican ni verifican casos reales de fraude.

La confianza en los mecanismos actuales de seguridad y reputación se distribuyó en la escala de 1 a 5, con {q6high} respuestas en los valores 4 o 5 (\textbf{{{pct(q6high)}\,\%}}). Entre las características que generaron mayor desconfianza se destacaron el precio considerablemente inferior al de ofertas comparables (\textbf{{{n(7,'Precio considerablemente inferior al de publicaciones similares.')} respuestas}}), la ausencia de calificaciones u opiniones (\textbf{{{n(7,'Ausencia de calificaciones u opiniones')}}}) y la solicitud de pago fuera de la plataforma (\textbf{{{n(7,'Solicitud de realizar pagos fuera de la plataforma')}}}). Se trata de percepciones de los participantes y no de una validación de esos indicadores como predictores de fraude.

\subsection{{Utilidad percibida e intención declarada de uso}}

Tras presentar una descripción conceptual de una herramienta independiente de análisis preventivo, \textbf{{{q8} participantes ({pct(q8)}\,\%)}} asignaron una utilidad de 4 o 5 en una escala de cinco puntos (figura~\ref{{fig:ml-encuesta-08}}). Además, \textbf{{{q9} ({pct(q9)}\,\%)}} manifestaron que probablemente utilizarían una herramienta gratuita con frecuencia o ante publicaciones que les generaran dudas (figura~\ref{{fig:ml-encuesta-09}}). Estas respuestas sugieren \emph{{interés declarado}} y no constituyen evidencia de adopción efectiva.

En cuanto a funcionalidades, la opción más señalada fue la información sobre el historial comercial del vendedor (\textbf{{{n(10,'Información sobre el historial comercial del vendedor')} respuestas; {pct(n(10,'Información sobre el historial comercial del vendedor'))}\,\%}}). Las advertencias sobre datos insuficientes y la explicación de los factores de riesgo reunieron {n(10,'Advertencias sobre información insuficiente o no disponible')} selecciones cada una. Entre las preocupaciones, destacaron la recopilación innecesaria de datos personales (\textbf{{{n(11,'Que recopile datos personales innecesarios')} respuestas}}), la información desactualizada (\textbf{{{n(11,'Que utilice información desactualizada')}}}) y las advertencias incorrectas (\textbf{{{n(11,'Que genere advertencias incorrectas')}}}). Estos resultados sirven para orientar prioridades de transparencia, privacidad y calidad de datos, pero por sí solos no validan decisiones técnicas específicas.

\subsection{{Distribución completa de respuestas}}

Las figuras siguientes presentan las frecuencias absolutas y los porcentajes observados para las once preguntas, incluida la opción de valoración no seleccionada en las escalas. En preguntas de selección múltiple, el denominador continúa siendo el número total de participantes ({N}).
'''
# add charts under thematic subsections to group close to text
figures=[]
for q in range(1,12):
    figures.append(rf'''\begin{{figure}}[H]
\centering
\includegraphics[width=0.94\textwidth,height=0.37\textheight,keepaspectratio]{{figuras/marketlens/encuesta/pregunta_{q:02d}.png}}
\caption{{{esc(GRAPH_CAPTIONS[q])} (n={N}).}}\label{{fig:ml-encuesta-{q:02d}}}
\end{{figure}}
''')
BODY+='\n'.join(figures)
BODY+=rf'''
\subsection{{Alcance y limitaciones del relevamiento}}

La distribución del formulario entre contactos y la participación voluntaria introducen posibles \textbf{{sesgos de selección y autoselección}}. El instrumento no relevó variables sociodemográficas ni verificó en forma independiente las experiencias declaradas. Por consiguiente, no es posible generalizar los resultados a la totalidad de compradores ni estimar márgenes de error de muestreo probabilístico. Asimismo, la descripción conceptual de MarketLens puede influir en las valoraciones de utilidad e intención de uso.

Estas evidencias complementan la justificación del problema abordado y permiten identificar prioridades expresadas por las personas encuestadas. No deben confundirse con pruebas de usabilidad del prototipo, validaciones de precisión del índice de riesgo o una medición de su impacto real en la prevención de estafas. El presente corte corresponde a {N} respuestas; de incorporarse nuevas respuestas, deben recalcularse todos los porcentajes y sustituirse los gráficos correspondientes.
'''
# Keep limitations with analysis, before the gallery of figures, to avoid a stranded trailing paragraph.
gallery_pos=BODY.index(r'\subsection{Distribución completa de respuestas}')
limits_pos=BODY.index(r'\subsection{Alcance y limitaciones del relevamiento}')
BODY=BODY[:gallery_pos]+BODY[limits_pos:]+'\n'+BODY[gallery_pos:limits_pos]
(OUT/'capitulos'/'07-resultados-encuesta.tex').write_text(BODY,encoding='utf-8')

# Full appendix: observed options + known scale 1..5. Report exact source-derived options.
APP=rf'''%!TEX root = ../main.tex
% Apéndice A — cuestionario derivado del CSV de respuestas, corte {cutstamp}.
% Si había opciones nunca seleccionadas, verificar su texto exacto en Google Forms.
\chapter{{Encuesta de validación exploratoria}}\label{{apx:encuesta}}
\section{{Objetivo y alcance}}

El objetivo de la encuesta fue explorar experiencias de compra, percepciones de seguridad y confianza en plataformas digitales, así como el interés potencial en una herramienta independiente de evaluación preventiva del riesgo. La encuesta no requirió interactuar con el software MarketLens ni pretendió medir su eficacia técnica. Se aplicó durante la etapa de documentación del proyecto, no antes del desarrollo del prototipo.

\section{{Metodología de aplicación}}

Se utilizó un cuestionario en línea de once preguntas cerradas: respuestas únicas, escalas de cinco puntos y selección de varias alternativas. La difusión se realizó a través de contactos del autor, mediante una muestra \textbf{{no probabilística por conveniencia}}. En el corte de datos analizado se registraron \textbf{{{N} respuestas completas}}, recibidas entre el {period_label}. El archivo exportado incluye una marca temporal y las once columnas de respuestas; no contiene campos explícitos de nombre o correo electrónico.

El análisis se efectuó mediante frecuencias y porcentajes descriptivos, tomando {N} como denominador para cada pregunta. En las preguntas de selección múltiple, una misma persona puede contribuir a varias categorías, por lo que los porcentajes no necesariamente suman 100\,\%. La participación voluntaria y el círculo de difusión limitan la representatividad de los resultados.

\section{{Presentación del cuestionario}}

El formulario se difundió mediante Google Forms en la dirección \href{{https://forms.gle/VtUtZDMNPApc3VeQ6}}{{formulario público en Google Forms}}. Su temática fue la seguridad y confianza en marketplaces digitales. Las preguntas iniciales exploraron hábitos y percepción de riesgo. Antes del bloque sobre utilidad y funcionalidades se presentó la idea de una herramienta independiente de análisis preventivo, aclarando que sus indicadores no permiten determinar con certeza si una publicación es fraudulenta.

\noindent\textit{{Nota de transcripción:}} las preguntas y las opciones enumeradas a continuación se recuperan de las respuestas exportadas. Si alguna opción del formulario no fue seleccionada por ninguna persona, podría no aparecer en el CSV y debe cotejarse con el formulario original antes de cerrar la versión definitiva del apéndice. Para facilitar la lectura se corrigió la errata ``verces'' por ``veces'' en una opción de frecuencia; los conteos se calcularon sin alterar los registros de origen.

\section{{Preguntas y opciones de respuesta}}
'''
for q in range(1,12):
    APP+=rf'\subsection*{{Pregunta {q}. {esc(questions[q-1])}}}'+'\n'
    typ=('Selección múltiple' if q in multiselect else ('Escala de 1 a 5' if q in (6,8) else 'Opción única'))
    APP+=rf'\noindent\textit{{Tipo: {typ}.}}'+'\n'+r'\begin{itemize}\setlength\itemsep{1pt}'+'\n'
    if q in (6,8): keys=[str(x) for x in range(1,6)]
    elif q in SINGLE_ORDER:keys=[x for x in SINGLE_ORDER[q] if x in counts[q]]
    else:keys=[x for x,_ in counts[q].most_common()]
    for key in keys:
        APP+=rf'\item {esc(short(key))}'+'\n'
    APP+=r'\end{itemize}'+'\n'
APP+=rf'''
\section{{Registro de resultados}}

Los resultados agregados, su interpretación y las figuras correspondientes se presentan en la sección~\ref{{sec:ml-resultados-encuesta}} del capítulo~\ref{{cap:resultados}}. El conjunto utilizado en este corte contiene {N} respuestas completas. Se preservaron exclusivamente conteos agregados para la documentación del informe, sin reproducir las marcas temporales ni filas individuales en este apéndice.
'''
(OUT/'apendices'/'A-encuesta-validacion.tex').write_text(APP,encoding='utf-8')

# Integrate chapter 7 from earlier adapted zip (checked against previous version).
import zipfile
CH7_ZIP=ROOT/'marketlens-capitulo-7-adaptado.zip'
if CH7_ZIP.exists():
    with zipfile.ZipFile(CH7_ZIP) as z:
        existing=z.read('capitulos/07-resultados.tex').decode('utf-8')
else:
    existing = None
if existing is not None:
    existing=existing.replace('Tampoco se atribuyen resultados de encuestas o entrevistas que no hayan sido realizadas.',
        'Se incorpora en este capítulo una encuesta exploratoria con respuestas reales, mientras que la entrevista a especialista permanece pendiente de realización.')
    existing=existing.replace('Como complemento de los resultados presentados, el \\textbf{Apéndice A}',
        'Como complemento de los resultados presentados, el \\textbf{Apéndice C}')
    existing=existing.rstrip()+'\n\n% Encuesta exploratoria incorporada a partir del corte del CSV.\n\\input{capitulos/07-resultados-encuesta}\n'
    (OUT/'capitulos'/'07-resultados.tex').write_text(existing,encoding='utf-8')

CH2_ZIP=ROOT/'MarketLens_Capitulo_02_Metodologia.zip'
if CH2_ZIP.exists():
    with zipfile.ZipFile(CH2_ZIP) as z:
        met=z.read('capitulos/02-metodologia.tex').decode('utf-8')
else: met=None
method=rf'''\subsection{{Relevamiento exploratorio mediante encuesta}}
\label{{subsec:ml-encuesta-metodo}}

Como complemento de las verificaciones técnicas se aplicó una encuesta exploratoria de carácter descriptivo, durante la etapa de documentación del proyecto, para conocer percepciones sobre la seguridad en marketplaces y el interés potencial en herramientas preventivas. Se empleó un formulario en línea con \textbf{{once preguntas cerradas}}: opciones únicas, escalas de 1 a 5 y selección múltiple. Las preguntas cubrieron hábitos de compra, criterios para valorar publicaciones, experiencias de desconfianza, percepción de los mecanismos actuales de protección, utilidad potencial y preocupaciones sobre herramientas independientes de evaluación.

La difusión se realizó mediante contactos del autor, por lo que la muestra es \textbf{{no probabilística por conveniencia}}. El corte considerado comprende \textbf{{{N} respuestas completas}} recibidas entre el {period_label}. Se analizaron frecuencias absolutas y porcentajes sobre el total de participantes; las preguntas que admitían varias elecciones se contabilizaron por opción, sin sumar sus porcentajes como si fueran categorías mutuamente excluyentes.

El objetivo de esta actividad fue explorar la \textbf{{necesidad percibida y el interés declarado}} por la propuesta, no medir satisfacción con el prototipo, cuantificar prevención efectiva de estafas ni evaluar la precisión del motor de riesgo. Se reconocen limitaciones de representatividad, posibles sesgos de autoselección y ausencia de verificación externa de las experiencias declaradas. El cuestionario se reproduce en el apéndice~\ref{{apx:encuesta}} y los resultados se exponen en el capítulo~\ref{{cap:resultados}}. La entrevista con especialista forma parte de las actividades previstas pero no se presenta como realizada.

'''
(OUT/'capitulos'/'02-metodologia-encuesta.tex').write_text(method,encoding='utf-8')
if met is not None:
    needle='\\section{Metodología de dirección del proyecto}'
    if needle not in met: raise ValueError('No encontrado anclaje cap 2')
    met=met.replace(needle,'\\input{capitulos/02-metodologia-encuesta}\n\n'+needle,1)
    met=met.replace('Salida de Maven; Apéndice B','Salida de Maven; Apéndice C')
    (OUT/'capitulos'/'02-metodologia.tex').write_text(met,encoding='utf-8')

# methodological and result figures reproducibility note
readme=f'''MARKETLENS — INTEGRACIÓN DE ENCUESTA (corte {cutstamp})
========================================================

Fuente: CSV adjuntado del formulario ({N} respuestas; corte {cutstamp}).
La URL del formulario no permitió verificar sus opciones no seleccionadas; cotejar
el Apéndice A contra el formulario antes de la entrega definitiva.

ARCHIVOS
--------
capitulos/07-resultados-encuesta.tex : sección con resultados reales y 11 figuras
capitulos/02-metodologia-encuesta.tex: método de la encuesta, regenerable
capitulos/07-resultados.tex          : versión integrada del capítulo 7 anterior
capitulos/02-metodologia.tex         : versión integrada del capítulo 2 anterior
apendices/A-encuesta-validacion.tex  : cuestionario y método del estudio
figuras/marketlens/encuesta/         : 11 gráficos PNG en alta resolución

datos_agregados/frecuencias_encuesta.csv: conteos agregados (sin filas individuales)
scripts/generar_graficos_encuesta.py : script reproducible de generación de este paquete

INTEGRAR EN EL REPOSITORIO
-------------------------
1. Copiar la carpeta figuras/marketlens/encuesta/ al repositorio.
2. Copiar capitulos/07-resultados-encuesta.tex al repositorio.
3. Elegir SOLO UNA vía para el capítulo 7:
   - Si NO modificaste 07-resultados.tex desde la versión anterior:
     reemplazarlo por capitulos/07-resultados.tex provisto aquí.
   - Si lo modificaste: conservar tu versión y agregar al final:
     \\input{{capitulos/07-resultados-encuesta}}
     Además cambiar el texto que dice que no hay encuesta y la antigua referencia
     al Apéndice A técnico, que ahora es el C.
4. Actualizar capitulos/02-metodologia.tex, reemplazándolo con la versión incluida,
   SOLO si no hiciste cambios propios desde la versión que preparamos. Si hay
   cambios, insertar manualmente \\input{{capitulos/02-metodologia-encuesta}} antes
   de la sección de dirección del proyecto y corregir Apéndice B técnico -> C.
5. Reemplazar apendices/A-encuesta-validacion.tex con la versión nueva.
6. Compilar el archivo main.tex DOS veces (o con latexmk) para resolver referencias.
7. Verificar que main.tex incorpore los capítulos 2, 7 y el Apéndice A.
8. No es necesario modificar refs.bib.

IMPORTANTE
----------
* Las {N} respuestas representan un corte PROVISORIO, no una encuesta cerrada.
* Las cifras son descriptivas, no representativas de los compradores de Argentina.
* Preguntas multiselección: un usuario puede marcar varias opciones. El
  porcentaje se calcula siempre sobre {N} participantes; puede superar 100%
  al sumar todas las opciones.
* La versión del Apéndice A enumera las opciones recuperables del CSV. Las
  opciones que nadie eligió pueden estar ausentes: comparar con Google Forms.
* El gráfico de escala incluye respuestas de valor cero cuando una opción no
  fue elegida (por ejemplo el valor 2 de la pregunta 8).
* No se ha realizado aún la entrevista, que sigue pendiente.
* Este paquete no contiene datos individuales ni sellos de tiempo.
* Se corrigió para visualización la errata '12 verces' del formulario a
  '12 veces'; los valores originales se conservan en el cálculo.

ACTUALIZACIÓN CON RESPUESTAS ADICIONALES
--------------------------------------
Colocar una nueva exportación CSV en un lugar conocido y ejecutar desde la raíz
con Python 3, Matplotlib instalado:
  python scripts/generar_graficos_encuesta.py "RUTA_AL_NUEVO_CSV.csv" "CARPETA_DE_SALIDA"

El script puede regenerar los gráficos, los fragmentos de capítulos y el Apéndice A
sin los ZIP anteriores; las versiones completas de los capítulos 02 y 07 no se
regeneran sin los ZIP originales. Si ya integraste esos capítulos con input, el
contenido y los datos se actualizan automáticamente al reemplazar los fragmentos.

Recomendación: antes de cerrar el documento, exportar nuevamente el CSV,
congelar la fecha del corte y regenerar los gráficos y porcentajes.
'''
(OUT/'LEEME_INTEGRACION.txt').write_text(readme,encoding='utf-8')
# file summary
print(f'Ficheros generados: {len(list(OUT.rglob("*")))}; N={N} records; e.g.: Q4={q4}, Q5={q5}, Q8 high={q8}, Q9 interest={q9}; output={OUT}')
