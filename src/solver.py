# src/solver.py
import time
from dataclasses import dataclass, field

import pulp

from src.modelo import ModeloConstruido


@dataclass
class SolucionCruda:
    """Salida directa del solver, sin interpretar."""
    estado: str                      # "Optimal", "Infeasible", "Unbounded", "Not Solved", "Undefined", "Sin demanda"
    mensaje: str                     # explicación legible del estado
    valor_objetivo: float | None
    valores_x: dict = field(default_factory=dict)   # (centro, zona, tipo) -> cantidad enviada
    valores_n: dict = field(default_factory=dict)   # (zona, tipo) -> demanda no atendida
    tiempo: float = 0.0              # segundos de resolución
    num_variables: int = 0
    num_restricciones: int = 0
    solver: str = ""                 # nombre del solver usado

    @property
    def tiene_solucion(self) -> bool:
        return self.estado == "Optimal"


_MENSAJES = {
    "Optimal": "Se encontró una solución óptima.",
    "Infeasible": (
        "El escenario no tiene solución factible. Revise las restricciones "
        "obligatorias: atención mínima en zonas críticas (alfa), reservas de "
        "inventario, rutas bloqueadas o capacidades de despacho y de ruta."
    ),
    "Unbounded": "El modelo no está acotado. Revise los datos del escenario.",
    "Not Solved": "El solver no terminó de resolver el modelo.",
    "Undefined": "El solver no pudo determinar el estado de la solución.",
}


def _crear_solver(mostrar_log: bool):
    """Elige el solver disponible: CBC (PuLP 3.x o anterior) o HiGHS (PuLP 4.x)."""
    if hasattr(pulp, "PULP_CBC_CMD"):
        cbc = pulp.PULP_CBC_CMD(msg=mostrar_log)
        if cbc.available():
            return cbc, "CBC"
    try:
        highs = pulp.HiGHS(msg=mostrar_log)
        if highs.available():
            return highs, "HiGHS"
    except Exception:
        pass
    raise RuntimeError(
        "No hay ningún solver disponible. Instale uno con: pip install highspy"
    )


def _normalizar_estado(estado) -> str:
    """Convierte el estado de cualquier versión de PuLP a un texto estándar."""
    nombre = getattr(estado, "name", str(estado))
    return {"NotSolved": "Not Solved"}.get(nombre, nombre)


def _valor(variable) -> float:
    """Lee el valor de una variable y elimina el ruido numérico."""
    v = variable.value() or 0.0
    if variable.cat == pulp.LpInteger:
        return int(round(v))
    return 0.0 if abs(v) < 1e-9 else v


def ejecutar_solver(modelo: ModeloConstruido, mostrar_log: bool = False) -> SolucionCruda:
    prob = modelo.problema

    # Escenario sin demanda: no hay nada que optimizar
    if modelo.num_variables == 0:
        return SolucionCruda(
            estado="Sin demanda",
            mensaje="El escenario no tiene demanda registrada, no hay nada que optimizar.",
            valor_objetivo=0.0,
        )

    solver, nombre_solver = _crear_solver(mostrar_log)

    inicio = time.perf_counter()
    resultado = prob.solve(solver)
    tiempo = time.perf_counter() - inicio

    # PuLP 3.x guarda el estado en prob.status (número); PuLP 4.x lo devuelve en el resultado
    if hasattr(prob, "status"):
        estado = pulp.LpStatus[prob.status]
    else:
        estado = _normalizar_estado(resultado.status)

    solucion = SolucionCruda(
        estado=estado,
        mensaje=_MENSAJES.get(estado, "El solver terminó sin una solución óptima."),
        valor_objetivo=None,
        tiempo=tiempo,
        num_variables=modelo.num_variables,
        num_restricciones=modelo.num_restricciones,
        solver=nombre_solver,
    )

    if estado == "Optimal":
        solucion.valor_objetivo = pulp.value(prob.objective)
        solucion.valores_x = {k: _valor(v) for k, v in modelo.x.items()}
        solucion.valores_n = {k: _valor(v) for k, v in modelo.n.items()}

    return solucion