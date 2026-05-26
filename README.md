# Ares v3.0 — Monitor del Sistema

Monitor de sistema de alto rendimiento para **Windows** y **macOS**, desarrollado con Python + PyQt6.
Rediseñado desde cero para ofrecer velocidad, claridad y una interfaz oscura minimalista.

---

# ¿Qué hay de nuevo en la v3.0?

| Característica                          | Detalle                                                                                              |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Motor de datos no bloqueante**        | `DataWorker` (QThread) recopila todas las métricas en segundo plano — la interfaz nunca se congela   |
| **Bus de datos unificado**              | Un único worker alimenta todas las pestañas mediante señales Qt; sin llamadas redundantes a `psutil` |
| **Vista de rendimiento completa**       | Los 5 gráficos de recursos visibles simultáneamente (sin seleccionar tarjetas)                       |
| **Barras CPU por núcleo**               | Uso en tiempo real para cada núcleo lógico con colores dinámicos                                     |
| **Tabla avanzada de procesos**          | Columna ASCII de CPU, memoria RSS en MB y actualizaciones incrementales                              |
| **Diferencial inteligente de procesos** | Solo inserta/elimina filas modificadas — evita reconstruir toda la tabla                             |
| **Actualización más rápida**            | Métricas del sistema a 1 Hz; lista de procesos a 0.33 Hz — configurable                              |
| **Interfaz oscura minimalista**         | Paleta navy/índigo, números monoespaciados y bordes finos                                            |
| **Sin dependencias de IA**              | Se eliminó la integración con Claude → no requiere API Key y consume menos recursos                  |

---

# Arquitectura

```text
main.py
│
├── core/workers/data_worker.py   ← QThread principal en segundo plano
│       │  emite: system_ready(dict)  process_ready(list)
│       │
├── core/data/          ← llamadas directas a psutil / sistema operativo
├── core/services/      ← lógica de negocio, caché y alertas
└── core/utils/         ← formateadores y utilidades

ui/
├── main_window.py      ← navegación lateral, barra de estado y tema
└── tabs/
    ├── processes_tab.py    ← tabla incremental y columnas avanzadas
    ├── performance_tab.py  ← 5 gráficos en vivo + núcleos CPU
    ├── network_tab.py      ← conexiones y estadísticas por interfaz
    ├── system_tab.py       ← información completa de hardware y SO
    ├── alerts_tab.py       ← configuración e historial de alertas
    └── services_tab.py     ← servicios de Windows (admin)
```

### Regla de dependencias

```text
UI → services → data
```

Nunca saltar capas.

---

# Inicio rápido

## macOS / Linux

```bash
git clone <repo>
cd ares-v3
bash run.sh
```

## Windows

```bat
run.bat
```

## Manual

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
.\venv\Scripts\activate

pip install -r requirements.txt

python main.py
```

---

# Requisitos

* Python 3.10+
* PyQt6 ≥ 6.4
* psutil ≥ 5.9
* pyqtgraph ≥ 0.13
* Windows 10+ o macOS 10.14+

---

# Pestañas

## ⚡ Procesos

* Tabla en vivo con:

  * Icono
  * PID
  * Nombre
  * CPU %
  * Barra ASCII
  * MEM %
  * RSS MB
  * Threads
  * Estado
* Actualizaciones incrementales
* Filtros por:

  * Nombre
  * CPU
  * Memoria
  * Estado
* Menú contextual:

  * Kill
  * Kill Tree
  * Suspend
  * Resume
  * Cambiar prioridad
  * Abrir ubicación
  * Ver detalles
* Exportación CSV

---

## 📊 Rendimiento

* Todos los recursos visibles simultáneamente:

  * CPU
  * Memoria
  * Disco
  * Red
  * GPU
* Gráficos dinámicos de 90 puntos
* Vista por núcleo CPU en tiempo real
* Score de salud del sistema (0–100)
* Selector de disco
* Selector de velocidad máxima de red

---

## 🌐 Red

* Bytes enviados/recibidos globalmente
* Estadísticas por interfaz (hasta 8 interfaces)
* Tabla de conexiones activas:

  * Dirección local/remota
  * Estado
  * Tipo
  * PID
* Actualización automática cada 3 segundos

---

## 🖥 Sistema

* Información completa del CPU:

  * Modelo
  * Núcleos físicos/lógicos
  * Frecuencias por núcleo
* Memoria detallada:

  * Total
  * Disponible
  * Usada
  * Caché
  * Swap
* Almacenamiento:

  * Particiones
  * Barra ASCII de uso
  * Sistema de archivos
* Sistema operativo
* Hostname
* Arquitectura
* Boot time
* Uptime

---

## 🔔 Alertas

* Umbrales configurables:

  * CPU
  * Memoria
  * Disco
  * GPU
* Niveles:

  * Warning
  * Critical
* Deduplicación inteligente:

  * La misma alerta solo aparece una vez por minuto
* Historial con colores
* Dismiss individual o global
* Limpiar historial

---

## ⚙ Servicios *(Solo Windows)*

* Lista completa de servicios
* Estado del servicio
* Iniciar / detener servicios *(requiere permisos de administrador)*

---

# Notas de rendimiento

| Configuración              | Valor            | Motivo                           |
| -------------------------- | ---------------- | -------------------------------- |
| Intervalo métricas sistema | 1.0 s            | Gráficos fluidos sin sobrecargar |
| Intervalo lista procesos   | 3.0 s            | `psutil` es costoso              |
| Historial gráficos         | 90 puntos        | ~1.5 minutos de historial        |
| Actualización tabla        | Diff incremental | Evita repaint completo           |
| OpenGL en pyqtgraph        | Desactivado      | Mejor compatibilidad             |

---

# Licencia

MIT — libre para usar, modificar y distribuir.
