# Resuelve el modelo con HiGHS y devuelve los valores de las variables
import time
import pulp
from dataclasses import dataclass, field
from src.modelo import ModeloConstruido


@dataclass
class SolucionCruda:
    estado: str                    # "Optimal", "Infeasible", "Unbounded", ...
    mensaje: str                   # explicación del estado para el usuario
    valor_objetivo: float | None = None
    valores_x: dict = field(default_factory=dict)   # (centro, zona, tipo) -> cantidad enviada
    valores_n: dict = field(default_factory=dict)   # (zona, tipo) -> demanda no atendida
    tiempo: float = 0.0            # segundos que tardó el solver
    num_variables: int = 0
    num_restricciones: int = 0
    solver: str = "HiGHS"

    @property
    def tiene_solucion(self):
        return self.estado == "Optimal"


MENSAJES = {
    "Optimal": "Se encontró una solución óptima.",
    "Infeasible": (
        "El escenario no tiene solución factible. Revise la atención mínima de las "
        "zonas críticas (alfa), las reservas de inventario, las rutas bloqueadas y "
        "las capacidades de despacho y de ruta."
    ),
    "Unbounded": "El modelo no está acotado. Revise los datos del escenario.",
}


def _limpiar(variable):
    """Valor de una variable sin el ruido numérico del solver."""
    valor = variable.value() or 0
    if variable.cat == pulp.LpInteger:
        return round(valor)
    return 0 if abs(valor) < 1e-9 else valor


def ejecutar_solver(modelo: ModeloConstruido, mostrar_log=False) -> SolucionCruda:
    # Sin demanda no hay nada que optimizar
    if modelo.num_variables == 0:
        return SolucionCruda("Sin demanda", "El escenario no tiene demanda registrada.", 0.0)

    inicio = time.perf_counter()
    resultado = modelo.problema.solve(pulp.HiGHS(msg=mostrar_log))
    tiempo = time.perf_counter() - inicio

    estado = resultado.status.name
    solucion = SolucionCruda(
        estado=estado,
        mensaje=MENSAJES.get(estado, f"El solver no encontró una solución óptima (estado: {estado})."),
        tiempo=tiempo,
        num_variables=modelo.num_variables,
        num_restricciones=modelo.num_restricciones,
    )

    if solucion.tiene_solucion:
        solucion.valor_objetivo = pulp.value(modelo.problema.objective)
        solucion.valores_x = {k: _limpiar(v) for k, v in modelo.x.items()}
        solucion.valores_n = {k: _limpiar(v) for k, v in modelo.n.items()}

    return solucion