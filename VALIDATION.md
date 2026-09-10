# Estado de validación

Fecha: 9 de septiembre de 2026. Entorno probado: Linux x86-64, Python 3.12.3 y GCC 13.3.0. Runtime: Hermes 0.21.1, radare2 6.2.2, radare2-mcp 1.8.8; revisiones exactas en `dependencies.lock.json`.

## Ampliación en curso: 33 artículos

La batería del 9 de septiembre de 2026 (`work/verification/20260909-155132/report.json`) preparó los **109 ejemplos**: **90 aprobados** con ejecución y breakpoint real en radare2/MCP; **19 incompletos**, todos Windows, con compilación y análisis estático aprobados y ejecución/depuración pendientes. No hubo fallos técnicos en esa batería. Estos controles no comprueban todavía todas las prácticas de cada artículo.

Las **15 pruebas de integración actuales pasan**. Incluyen las 11 de la primera versión, análisis JSON de un PE grande sin truncamiento, los hashes de los 109 originales y espacios de trabajo independientes, ejecución/depuración de i386 con el runtime privado, y restauración de calling conventions al cambiar de archivo. La prueba de parcheo también comprueba que cerrar y volver a iniciar conserva el binario modificado.

La evaluación sistemática con Hermes completó los **33 artículos**: **30 aprobados** con integración real (MCP + radare2 + snapshot + respuesta guardada) y **3 reading-only** (malware1, malware3, malware4: muestra original ausente o entorno Windows necesario). El harness guarda automáticamente la respuesta del modelo, la nota y el snapshot de evidencia desde la base de datos de Hermes, sin depender de que el modelo recuerde hacerlo al final. Las sesiones estancadas de ejecuciones anteriores se limpian automáticamente.

Emotet: muestra exacta del artículo recuperada por hash; extracción VBA/formularios y decodificación base64 UTF-16 comprobadas, con las cinco URL. IceID: PE desempaquetado original del blog; extracción RC4 de configuración comprobada. Ninguna de estas muestras se ha ejecutado.

Pendientes para el 100 %: prácticas avanzadas completas, entorno Windows aislado y muestras originales ausentes. Los enlaces originales de Ziraat, Dridex y Ramnit devolvieron HTTP 404. El capítulo 2 sigue conservando el error editorial del origen: el índice anuncia condicionales, pero el archivo contiene buffer overflows.

Los apartados siguientes conservan el detalle de la validación inicial como antecedente, con sus cifras originales.

## Pruebas de integración iniciales

`python3 -m unittest discover -s tests -v`: **11 pruebas aprobadas**, con compilador y servidor reales y sin consumo de API.

- Los 33 Markdown coinciden con sus hashes de origen; la discrepancia del capítulo 2 queda registrada.
- Recompilar conserva las modificaciones del lector y registra el ejecutable producido.
- Dos clientes comparten dirección, flags y comentarios. Reutilizar el laboratorio conserva el servidor; cambiar de laboratorio exige cerrarlo. Una petición HTTP sin el token del servidor devuelve 401.
- Un breakpoint en el ejemplo Books detiene realmente la ejecución y permite leer ambos identificadores en la pila.
- Parchear la cadena del primer ejemplo cambia su salida de `Hello, World!` a `Jello, World!` al ejecutar el binario.
- La prueba de layout mide el tipo C y reconoce cambios de fuente posteriores a la compilación.
- Si otro cliente abre un archivo distinto, el snapshot identifica ese archivo como objetivo actual.
- Notas, progreso y evidencias sobreviven al reinicio del servidor.
- Las notas desde archivo conservan comillas, saltos de línea y texto con sintaxis de shell.
- Cambiar de proveedor descarta la ruta de la credencial anterior y actualiza el endpoint del perfil.
- El resolver real de Hermes selecciona el endpoint y la credencial configurados, tanto para OpenRouter como para un endpoint personalizado, usando una clave ficticia sin peticiones a modelos.

## Prueba con un modelo real

Se usó OpenRouter con `anthropic/claude-sonnet-4.6`, leyendo la credencial autorizada desde su archivo al arrancar. Hubo dos conversaciones y una reanudación. La primera encontró problemas de acceso al depurador; se corrigió la configuración del servidor y se repitió la prueba. La conversación posterior también agotó su presupuesto de herramientas antes de guardar todo; la reanudación completó las notas, evidencias y registro `ai_completed`.

La reanudación reconoció el comentario `reader-checkpoint-2026`, añadido manualmente desde otro cliente, y continuó sobre el proceso ya detenido. Esto comprueba que el agente consulta el estado compartido y puede retomar el trabajo.

En el binario Books generado en esta máquina se observaron:

| Comprobación | Resultado |
| --- | --- |
| Identificadores leídos en memoria | 6495407 y 6495700 |
| Desplazamiento de `book_id` dentro del tipo | 200 bytes |
| `sizeof(struct Books)` medido con C | 204 bytes |
| `_Alignof(struct Books)` medido con C | 4 bytes |
| Separación observada entre las dos variables locales | 208 bytes |

El modelo dedujo inicialmente tamaño 208 y alineación 8 a partir de la separación entre las variables. La comprobación independiente con `coursectl layout 6` permitió corregirlo. La separación de 208 bytes es una observación sobre esta compilación; no determina por sí sola la alineación del tipo ni demuestra por qué el compilador eligió esa distribución. Las instrucciones del agente ahora piden contrastar esa inferencia y distinguir observaciones de hipótesis.

Los registros de Hermes contabilizaron 48 llamadas al modelo y 78 llamadas a herramientas, con un coste **estimado por Hermes de 0,81 USD**. No es un importe confirmado de la factura de OpenRouter. Las conversaciones y registros permanecen en el directorio privado `work/` y no se incorporan al código del proyecto.

Esta prueba valida el funcionamiento de la integración y su recuperación entre sesiones. No constituye una evaluación sistemática de la calidad del tutor ni una validación de los laboratorios del curso completo.
