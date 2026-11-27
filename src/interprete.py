from dataclasses import dataclass, field

from src.modelo import ModeloConstruido
from src.solver import SolucionCruda

_TOL = 1e-9


@dataclass
class RutaUsada:
    centro: str
    zona: str
    cantidades: dict          # tipo -> cantidad enviada por esta ruta
    total: float              # unidades totales enviadas por la ruta
    costo: float              # costo de transporte de la ruta


@dataclass
class ResumenResultados:
    """Todo lo que pide el §12 del enunciado, listo para que la interfaz lo muestre."""
    # Estado y datos de la ejecución (también sirven para la tabla del §13)
    estado: str
    mensaje: str
    solver: str = ""
    tiempo: float = 0.0
    num_variables: int = 0
    num_restricciones: int = 0
    valor_objetivo: float | None = None

    # Cobertura (en porcentaje, 0 a 100)
    cobertura_global: float = 0.0
    cobertura_por_zona: dict = field(default_factory=dict)    # zona -> %
    cobertura_por_tipo: dict = field(default_factory=dict)    # tipo -> %

    # Totales de demanda (en la unidad común del escenario)
    demanda_total: float = 0.0
    demanda_atendida_total: float = 0.0
    demanda_no_atendida_total: float = 0.0

    # Detalle por zona y tipo: (zona, tipo) -> cantidad
    demanda_atendida: dict = field(default_factory=dict)
    demanda_no_atendida: dict = field(default_factory=dict)

    # Envíos y recepciones: entidad -> {tipo: cantidad}
    enviado_por_centro: dict = field(default_factory=dict)
    recibido_por_zona: dict = field(default_factory=dict)
    inventario_restante: dict = field(default_factory=dict)

    # Rutas y costo
    rutas_usadas: list = field(default_factory=list)          # lista de RutaUsada
    costo_total: float = 0.0

    @property
    def tiene_solucion(self) -> bool:
        return self.estado == "Optimal"


def _porcentaje(parte: float, total: float) -> float:
    return 100.0 * parte / total if total > _TOL else 0.0


def interpretar(modelo: ModeloConstruido, solucion: SolucionCruda) -> ResumenResultados:
    """Convierte la salida cruda del solver en los resultados que ve el usuario."""
    resumen = ResumenResultados(
        estado=solucion.estado,
        mensaje=solucion.mensaje,
        solver=solucion.solver,
        tiempo=solucion.tiempo,
        num_variables=solucion.num_variables,
        num_restricciones=solucion.num_restricciones,
        valor_objetivo=solucion.valor_objetivo,
    )
    if not solucion.tiene_solucion:
        return resumen

    esc = modelo.escenario
    x = solucion.valores_x
    n = solucion.valores_n

    # ---------- Demanda atendida y no atendida por (zona, tipo) ----------
    for (z, t), pendiente in n.items():
        demanda = next(zona.demanda[t] for zona in esc.zonas if zona.nombre == z)
        no_atendida = max(0.0, pendiente)
        resumen.demanda_no_atendida[(z, t)] = no_atendida
        resumen.demanda_atendida[(z, t)] = max(0.0, demanda - no_atendida)

    resumen.demanda_total = sum(
        resumen.demanda_atendida[k] + resumen.demanda_no_atendida[k]
        for k in resumen.demanda_atendida
    )
    resumen.demanda_atendida_total = sum(resumen.demanda_atendida.values())
    resumen.demanda_no_atendida_total = sum(resumen.demanda_no_atendida.values())
    resumen.cobertura_global = _porcentaje(
        resumen.demanda_atendida_total, resumen.demanda_total
    )

    # ---------- Cobertura por zona y por tipo de ayuda ----------
    for zona in esc.zonas:
        claves = [k for k in resumen.demanda_atendida if k[0] == zona.nombre]
        if claves:
            atendida = sum(resumen.demanda_atendida[k] for k in claves)
            total = atendida + sum(resumen.demanda_no_atendida[k] for k in claves)
            resumen.cobertura_por_zona[zona.nombre] = _porcentaje(atendida, total)

    for tipo in esc.tipos:
        claves = [k for k in resumen.demanda_atendida if k[1] == tipo.nombre]
        if claves:
            atendida = sum(resumen.demanda_atendida[k] for k in claves)
            total = atendida + sum(resumen.demanda_no_atendida[k] for k in claves)
            resumen.cobertura_por_tipo[tipo.nombre] = _porcentaje(atendida, total)

    # ---------- Enviado por centro, recibido por zona e inventario restante ----------
    for centro in esc.centros:
        resumen.enviado_por_centro[centro.nombre] = {t.nombre: 0.0 for t in esc.tipos}
    for zona in esc.zonas:
        resumen.recibido_por_zona[zona.nombre] = {t.nombre: 0.0 for t in esc.tipos}

    for (c, z, t), cantidad in x.items():
        resumen.enviado_por_centro[c][t] += cantidad
        resumen.recibido_por_zona[z][t] += cantidad

    for centro in esc.centros:
        resumen.inventario_restante[centro.nombre] = {
            t.nombre: centro.inventario.get(t.nombre, 0)
            - resumen.enviado_por_centro[centro.nombre][t.nombre]
            for t in esc.tipos
        }

    # ---------- Rutas usadas y costo total ----------
    por_ruta: dict = {}
    for (c, z, t), cantidad in x.items():
        if cantidad > _TOL:
            por_ruta.setdefault((c, z), {})[t] = cantidad

    for (c, z), cantidades in por_ruta.items():
        ruta = esc.ruta_entre(c, z)
        total = sum(cantidades.values())
        costo = (ruta.costo if ruta else 0.0) * total
        resumen.rutas_usadas.append(
            RutaUsada(centro=c, zona=z, cantidades=cantidades, total=total, costo=costo)
        )
    resumen.costo_total = sum(r.costo for r in resumen.rutas_usadas)

    return resumen


def formatear_resumen(r: ResumenResultados) -> str:
    """Versión en texto del resumen, útil para consola y para probar sin interfaz."""
    lineas = [f"Estado: {r.estado} - {r.mensaje}"]
    if not r.tiene_solucion:
        return "\n".join(lineas)

    lineas += [
        f"Solver: {r.solver} | variables: {r.num_variables} | "
        f"restricciones: {r.num_restricciones} | tiempo: {r.tiempo:.4f} s",
        f"Valor de la función objetivo: {r.valor_objetivo:.6f}",
        f"Cobertura global: {r.cobertura_global:.2f}%",
        f"Demanda total: {r.demanda_total:g} | atendida: {r.demanda_atendida_total:g} | "
        f"no atendida: {r.demanda_no_atendida_total:g}",
        "Cobertura por zona: "
        + ", ".join(f"{z} {p:.2f}%" for z, p in r.cobertura_por_zona.items()),
        "Cobertura por tipo: "
        + ", ".join(f"{t} {p:.2f}%" for t, p in r.cobertura_por_tipo.items()),
        "Enviado por centro:",
    ]
    for c, tipos in r.enviado_por_centro.items():
        lineas.append(f"  {c}: " + ", ".join(f"{t}={q:g}" for t, q in tipos.items()))
    lineas.append("Recibido por zona:")
    for z, tipos in r.recibido_por_zona.items():
        lineas.append(f"  {z}: " + ", ".join(f"{t}={q:g}" for t, q in tipos.items()))
    lineas.append("Demanda no atendida:")
    for (z, t), q in r.demanda_no_atendida.items():
        if q > _TOL:
            lineas.append(f"  {z} / {t}: {q:g}")
    lineas.append("Rutas usadas:")
    for ru in r.rutas_usadas:
        detalle = ", ".join(f"{t}={q:g}" for t, q in ru.cantidades.items())
        lineas.append(f"  {ru.centro} -> {ru.zona}: {detalle} (costo {ru.costo:g})")
    lineas.append(f"Costo total de transporte: {r.costo_total:g}")
    lineas.append("Inventario restante:")
    for c, tipos in r.inventario_restante.items():
        lineas.append(f"  {c}: " + ", ".join(f"{t}={q:g}" for t, q in tipos.items()))
    return "\n".join(lineas)