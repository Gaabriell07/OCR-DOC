# Decisiones de interfaz

Aplicación local para una abogada que ya utiliza Word. Prioridad: convertir un
escaneo con pocas decisiones y bajo consumo de memoria.

Refero: se leyó refero-design y su referencia craft-details.md. Las búsquedas de
estilos y pantallas devolvieron NO_SUBSCRIPTION; no se atribuyen referencias
visuales que no pudieron consultarse. Se aplica el respaldo de craft del skill.

Dirección fijada para implementación directa: herramienta de trabajo blanca,
tipografía sans serif del sistema, textos oscuros, acento verde reservado a la
acción principal, bordes suaves y sin animaciones o recursos remotos.

| Decisión | Fuente | Motivo |
|---|---|---|
| Cargar → revisar → descargar | Flujo descrito por el usuario | Continuar trabajando en Word |
| Botones con verbos y campos etiquetados | craft-details: forms y copy | Evitar acciones ambiguas |
| Una página visible y procesada a la vez | Usuario: poca RAM; craft: performance | No acumular imágenes descomprimidas |
| Original junto al texto | Necesidad de revisión OCR | Comparar nombres y cifras |
| Selección opcional de franjas superior/inferior | Usuario: sellos al final | Conservar firmas sin prometer detección infalible |
| Sin ilustraciones ni fuentes externas | Usuario: aplicación sencilla y local | Menos carga y dependencias |

Los sellos se conservan como recortes de imagen. Su ubicación es aproximada en
Word; no se presenta como conversión de maquetación exacta.
