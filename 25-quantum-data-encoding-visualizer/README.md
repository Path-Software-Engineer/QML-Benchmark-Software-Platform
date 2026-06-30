# 25-quantum-data-encoding-visualizer

## 🧠 Descripción

Visualizador de estrategias de **quantum data encoding**.

Este proyecto pertenece a la ruta:

```txt
Building Projects
```

y acompaña directamente al proyecto:

```txt
AI Engineer Proyecto 49 — quantum-data-encoding-lab
```

Mientras AI Engineer profundiza en basis encoding, angle encoding, amplitude encoding conceptual, feature maps, número de qubits, profundidad de circuito y límites de escalabilidad, este Building Project convierte esas estrategias en visuales, tablas y tarjetas explicativas.

La idea es mostrar:

```txt
dataset clásico
→ features
→ normalización
→ encoding
→ circuito conceptual
→ qubits requeridos
→ profundidad
→ comparación
→ visualizer
```

Este proyecto no busca crear un modelo QML completo.

Busca explicar cómo entran los datos clásicos al mundo cuántico.

---

## 🎯 Objetivo

Crear un visualizador que compare estrategias de quantum data encoding.

El objetivo es explicar:

* Qué datos clásicos entran.
* Qué features se seleccionan.
* Cómo se representan en basis encoding.
* Cómo se representan en angle encoding.
* Qué significa amplitude encoding conceptualmente.
* Qué costo tiene cada encoding.
* Qué límites aparecen.
* Qué encoding conviene según el caso.

---

## 👤 Usuario objetivo

* Estudiante de Quantum Machine Learning.
* AI Engineer en formación.
* Persona que quiere entender QML desde la entrada de datos.
* Reclutador técnico viendo evidencia conceptual.
* Yo mismo como constructor de portafolio visual.

---

## 🧱 Arquitectura esperada

```txt
Classical Dataset
      ↓
Feature Selection
      ↓
Normalization
      ↓
Basis Encoding View
      ↓
Angle Encoding View
      ↓
Amplitude Encoding Concept
      ↓
Feature Map Cards
      ↓
Encoding Comparison Dashboard
```

---

## 🔁 Flujo técnico

```txt
load small dataset
→ select features
→ normalize values
→ map to encoding strategies
→ compare qubits and circuit depth
→ generate visual cards
→ export encoding visualizer
```

---

## 🧩 Módulos

### Módulo 1 — Classical Dataset View

Mostrar un dataset clásico pequeño.

Incluye:

* Features.
* Valores.
* Normalización.
* Límites del dataset.
* Selección de columnas.
* Notas de preparación.

Pregunta central:

```txt
¿Qué datos clásicos quiero codificar en un circuito?
```

---

### Módulo 2 — Feature Selection Notes

Explicar por qué se eligen pocas features.

Incluye:

* Features seleccionadas.
* Features descartadas.
* Relación entre features y qubits.
* Costo de escalar dimensiones.
* Riesgo de dataset demasiado grande.

Pregunta central:

```txt
¿Por qué QML exige pensar con cuidado qué features entran?
```

---

### Módulo 3 — Basis Encoding Card

Explicar basis encoding.

Incluye:

* Bits clásicos.
* Estados base.
* Ejemplo binario.
* Qubits requeridos.
* Ventaja.
* Limitación.

Pregunta central:

```txt
¿Cómo represento datos usando estados base?
```

---

### Módulo 4 — Angle Encoding Card

Explicar angle encoding.

Incluye:

* Feature como ángulo.
* Rotación.
* Normalización.
* Circuito conceptual.
* Ventaja.
* Limitación.

Pregunta central:

```txt
¿Cómo convierto features numéricas en rotaciones?
```

---

### Módulo 5 — Amplitude Encoding Concept Card

Explicar amplitude encoding de forma conceptual.

Incluye:

* Vector de features.
* Amplitudes.
* Normalización.
* Compresión.
* Costo de preparación.
* Advertencia.

Pregunta central:

```txt
¿Por qué amplitude encoding puede ser potente pero difícil de preparar?
```

---

### Módulo 6 — Feature Map Visual

Crear visual de feature map.

Incluye:

* Inputs.
* Rotaciones.
* Posible entrelazamiento.
* Profundidad.
* Uso en kernel.
* Limitación.

Pregunta central:

```txt
¿Cómo transforma un feature map los datos clásicos?
```

---

### Módulo 7 — Encoding Comparison Dashboard

Crear dashboard comparativo.

Debe mostrar:

* Encoding.
* Qubits requeridos.
* Profundidad conceptual.
* Facilidad de implementación.
* Escalabilidad.
* Uso recomendado.
* Limitaciones.

Pregunta central:

```txt
¿Qué encoding usaría según el problema y por qué?
```

---

## 🧪 Labs

### tec-labs

* `tec-classical-dataset-view-lab`
* `tec-feature-selection-notes-lab`
* `tec-basis-encoding-card-lab`
* `tec-angle-encoding-card-lab`
* `tec-amplitude-encoding-concept-lab`
* `tec-feature-map-visual-lab`
* `tec-encoding-comparison-dashboard-lab`

### docs-labs

* `docs-qml-encoding-storytelling-lab`
* `docs-encoding-comparison-template-lab`

### cloud-labs

* `cloud-encoding-report-to-gcp-storage-lab`
* `cloud-encoding-report-to-aws-s3-lab`
* `cloud-encoding-report-to-azure-blob-lab`

---

## 📊 Métricas / Evidencia

Este proyecto puede generar:

* Dataset clásico.
* Features seleccionadas.
* Normalización.
* Basis encoding card.
* Angle encoding card.
* Amplitude encoding concept.
* Feature map visual.
* Qubit count notes.
* Circuit depth notes.
* Encoding comparison dashboard.
* Capturas.
* README profesional.

---

## 🚀 Estado actual

Pendiente / por iniciar.

---

## 🧭 Ciclo de trabajo

```txt
Semana 1 → Dataset clásico, features y normalization notes
Semana 2 → Basis encoding, angle encoding y amplitude encoding concept
Semana 3 → Feature map visual y comparison dashboard
Semana 4 → Labs, README, capturas y cierre
```

---

## 📌 Próximos pasos

* Elegir dataset pequeño.
* Seleccionar pocas features.
* Normalizar valores.
* Crear basis encoding card.
* Crear angle encoding card.
* Crear amplitude encoding concept card.
* Crear feature map visual.
* Crear tabla comparativa.
* Preparar dashboard.
* Documentar labs.
* Agregar capturas.
* Publicar repo.

---

## ✅ Entregable final

Al terminar este proyecto debe existir:

* Quantum data encoding visualizer.
* Dataset clásico pequeño.
* Feature selection notes.
* Basis encoding card.
* Angle encoding card.
* Amplitude encoding concept card.
* Feature map visual.
* Encoding comparison dashboard.
* Labs documentados.
* README profesional.
* Capturas u outputs visibles.
* Conexión clara con `quantum-data-encoding-lab`.

---

## 🧭 Regla final

```txt
Antes de hablar de QML,
debo saber cómo entran los datos al circuito.

Encoding no es detalle.
Encoding condiciona todo el modelo.
```

Este proyecto debe demostrar que puedo explicar la entrada de datos a QML de forma visual, clara y responsable.
