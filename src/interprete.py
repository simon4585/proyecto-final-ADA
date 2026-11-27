# Convierte la salida del solver en los resultados que se muestran al usuario (§12)
from dataclasses import dataclass, field
from src.modelo import ModeloConstruido
from src.solver import SolucionCruda


@dataclass
class ResumenResultados:
    # Estado y datos de la ejecución (sirven también para la tabla del §13)
    estado: str
    mensaje: str
    solver: str = ""
    tiempo: float = 0.0
    num_variables: int = 0
    num_restricciones: int = 0
    valor_objetivo: float | None = None

    # Cobertura en porcentaje (0 a 100)
    cobertura_global: float = 0.0
    cobertura_por_zona: dict = field(default_factory=dict)    # zona -> %
    cobertura_por_tipo: dict = field(default_factory=dict)    # tipo -> %

    # Totales de demanda (en la unidad común del escenario)
    demanda_total: float = 0.0
    demanda_atendida_total: float = 0.0
    demanda_no_atendida_total: float = 0.0

    # Detalle por (zona, tipo)
    demanda_atendida: dict = field(default_factory=dict)
    demanda_no_atendida: dict = field(default_factory=dict)

    # entidad -> {tipo: cantidad}
    enviado_por_centro: dict = field(default_factory=dict)
    recibido_por_zona: dict = field(default_factory=dict)
    inventario_restante: dict = field(default_factory=dict)

    # Rutas con envíos: (centro, zona) -> {tipo: cantidad}, y su costo
    rutas_usadas: dict = field(default_factory=dict)
    costo_por_ruta: dict = field(default_factory=dict)
    costo_total: float = 0.0

    @property
    def tiene_solucion(self):
        return self.estado == "Optimal"


def porcentaje(parte, total):
    return 100 * parte / total if total > 0 else 0


def interpretar(modelo: ModeloConstruido, solucion: SolucionCruda) -> ResumenResultados:
    r = ResumenResultados(
        estado=solucion.estado,
        mensaje=solucion.mensaje,
        solver=solucion.solver,
        tiempo=solucion.tiempo,
        num_variables=solucion.num_variables,
        num_restricciones=solucion.num_restricciones,
        valor_objetivo=solucion.valor_objetivo,
    )
    if not solucion.tiene_solucion:
        return r

    esc = modelo.escenario
    tipos = [t.nombre for t in esc.tipos]

    # ----- Demanda atendida y no atendida, y cobertura por zona y por tipo -----
    atendida_zona, total_zona = {}, {}
    atendida_tipo, total_tipo = {}, {}
    for z in esc.zonas:
        for t, demanda in z.demanda.items():
            if demanda <= 0:
                continue
            no_atendida = solucion.valores_n[z.nombre, t]
            atendida = demanda - no_atendida
            r.demanda_no_atendida[z.nombre, t] = no_atendida
            r.demanda_atendida[z.nombre, t] = atendida

            atendida_zona[z.nombre] = atendida_zona.get(z.nombre, 0) + atendida
            total_zona[z.nombre] = total_zona.get(z.nombre, 0) + demanda
            atendida_tipo[t] = atendida_tipo.get(t, 0) + atendida
            total_tipo[t] = total_tipo.get(t, 0) + demanda

    r.demanda_total = sum(total_zona.values())
    r.demanda_atendida_total = sum(r.demanda_atendida.values())
    r.demanda_no_atendida_total = sum(r.demanda_no_atendida.values())
    r.cobertura_global = porcentaje(r.demanda_atendida_total, r.demanda_total)
    r.cobertura_por_zona = {z: porcentaje(atendida_zona[z], total_zona[z]) for z in total_zona}
    r.cobertura_por_tipo = {t: porcentaje(atendida_tipo[t], total_tipo[t]) for t in total_tipo}

    # ----- Enviado por centro, recibido por zona y rutas usadas -----
    r.enviado_por_centro = {c.nombre: {t: 0 for t in tipos} for c in esc.centros}
    r.recibido_por_zona = {z.nombre: {t: 0 for t in tipos} for z in esc.zonas}

    for (c, z, t), cantidad in solucion.valores_x.items():
        r.enviado_por_centro[c][t] += cantidad
        r.recibido_por_zona[z][t] += cantidad
        if cantidad > 0:
            r.rutas_usadas.setdefault((c, z), {})[t] = cantidad

    # ----- Costo de transporte -----
    for (c, z), cantidades in r.rutas_usadas.items():
        ruta = esc.ruta_entre(c, z)
        r.costo_por_ruta[c, z] = ruta.costo * sum(cantidades.values())
    r.costo_total = sum(r.costo_por_ruta.values())

    # ----- Inventario que queda en cada centro -----
    for c in esc.centros:
        r.inventario_restante[c.nombre] = {
            t: c.inventario.get(t, 0) - r.enviado_por_centro[c.nombre][t] for t in tipos
        }

    return r


# ---------------------------------------------------------------
# Solo para probar por consola; se puede borrar cuando la interfaz muestre los resultados
# ---------------------------------------------------------------
def formatear_resumen(r: ResumenResultados) -> str:
    lineas = [f"Estado: {r.estado} - {r.mensaje}"]
    if not r.tiene_solucion:
        return "\n".join(lineas)

    def lista(d):
        return ", ".join(f"{k}={v:g}" for k, v in d.items())

    lineas += [
        f"Solver: {r.solver} | variables: {r.num_variables} | "
        f"restricciones: {r.num_restricciones} | tiempo: {r.tiempo:.4f} s",
        f"Función objetivo: {r.valor_objetivo:.6f}",
        f"Cobertura global: {r.cobertura_global:.2f}%",
        f"Demanda total: {r.demanda_total:g} | atendida: {r.demanda_atendida_total:g} | "
        f"no atendida: {r.demanda_no_atendida_total:g}",
        "Cobertura por zona: " + ", ".join(f"{z} {p:.2f}%" for z, p in r.cobertura_por_zona.items()),
        "Cobertura por tipo: " + ", ".join(f"{t} {p:.2f}%" for t, p in r.cobertura_por_tipo.items()),
        "Enviado por centro:",
    ]
    lineas += [f"  {c}: {lista(d)}" for c, d in r.enviado_por_centro.items()]
    lineas.append("Recibido por zona:")
    lineas += [f"  {z}: {lista(d)}" for z, d in r.recibido_por_zona.items()]
    lineas.append("Demanda no atendida:")
    lineas += [f"  {z} / {t}: {q:g}" for (z, t), q in r.demanda_no_atendida.items() if q > 0]
    lineas.append("Rutas usadas:")
    lineas += [
        f"  {c} -> {z}: {lista(d)} (costo {r.costo_por_ruta[c, z]:g})"
        for (c, z), d in r.rutas_usadas.items()
    ]
    lineas.append(f"Costo total de transporte: {r.costo_total:g}")
    lineas.append("Inventario restante:")
    lineas += [f"  {c}: {lista(d)}" for c, d in r.inventario_restante.items()]
    return "\n".join(lineas)